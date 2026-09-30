// メニューの開け閉めと、画像の拡大表示
(function () {
  var body = document.body;
  var ham = document.querySelector('.hamburger');
  if (ham) ham.addEventListener('click', function () {
    var open = body.classList.toggle('nav-open');
    ham.setAttribute('aria-expanded', open);
  });
  document.querySelectorAll('.sub-toggle').forEach(function (b) {
    b.addEventListener('click', function () {
      var li = b.parentElement;
      li.classList.toggle('open');
      b.textContent = li.classList.contains('open') ? '－' : '＋';
    });
  });

  var box = document.querySelector('.lightbox');
  if (!box) return;
  var img = box.querySelector('img'), cap = box.querySelector('figcaption');
  var list = [], idx = 0;
  function show(i) {
    idx = (i + list.length) % list.length;
    var a = list[idx];
    img.src = a.getAttribute('href');
    cap.textContent = a.dataset.caption || '';
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a.lb');
    if (!a) return;
    e.preventDefault();
    list = Array.prototype.slice.call(a.closest('.gallery').querySelectorAll('a.lb'));
    show(list.indexOf(a));
    box.hidden = false;
  });
  function close() { box.hidden = true; img.src = ''; }
  box.querySelector('.lb-close').onclick = close;
  box.querySelector('.lb-prev').onclick = function () { show(idx - 1); };
  box.querySelector('.lb-next').onclick = function () { show(idx + 1); };
  box.addEventListener('click', function (e) { if (e.target === box) close(); });
  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowLeft') show(idx - 1);
    if (e.key === 'ArrowRight') show(idx + 1);
  });
})();
