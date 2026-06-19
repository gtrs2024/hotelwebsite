/* ═══════════════════════════════════════════════
   Elara Fine Dining — Main JavaScript
   ═══════════════════════════════════════════════ */

// ── Navbar scroll behaviour ───────────────────────
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });
}

// ── Mobile navigation ─────────────────────────────
const navToggle  = document.getElementById('navToggle');
const navMobile  = document.getElementById('navMobile');
const navClose   = document.getElementById('navClose');

if (navToggle && navMobile) {
  navToggle.addEventListener('click', () => {
    navMobile.classList.add('open');
    document.body.style.overflow = 'hidden';
  });
}
if (navClose && navMobile) {
  navClose.addEventListener('click', closeNav);
}
function closeNav() {
  if (navMobile) {
    navMobile.classList.remove('open');
    document.body.style.overflow = '';
  }
}

// ── Scroll reveal animations ──────────────────────
function triggerReveal() {
  const reveals = document.querySelectorAll('.reveal:not(.visible)');
  const windowH = window.innerHeight;

  reveals.forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < windowH - 80) {
      el.classList.add('visible');
    }
  });
}

window.addEventListener('scroll', triggerReveal, { passive: true });
window.addEventListener('resize', triggerReveal, { passive: true });
document.addEventListener('DOMContentLoaded', () => {
  // small delay so CSS transitions fire properly
  setTimeout(triggerReveal, 120);
});

// ── Smooth anchor scroll ──────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    const target = document.querySelector(link.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// ── Set min date on reservation form ─────────────
const dateInput = document.getElementById('preferred_date');
if (dateInput && !dateInput.value) {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  dateInput.min = tomorrow.toISOString().split('T')[0];
}

// ── Lazy image error fallback ─────────────────────
document.querySelectorAll('img').forEach(img => {
  img.addEventListener('error', function () {
    this.style.background = '#1a1a1a';
    this.style.minHeight  = '200px';
  });
});
