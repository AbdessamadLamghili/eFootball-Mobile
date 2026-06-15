/* ============================================================
   eFootball Rewards — Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Theme toggle ─────────────────────────────────────────
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');

  const savedTheme = localStorage.getItem('theme') || 'dark';
  html.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const current = html.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      updateThemeIcon(next);
    });
  }

  function updateThemeIcon(theme) {
    if (!themeIcon) return;
    themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
  }

  // ── Navbar notification dropdown ──────────────────────────
  const notifBtn = document.getElementById('notifBtn');
  const notifPanel = document.getElementById('notifPanel');

  if (notifBtn && notifPanel) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifPanel.classList.toggle('open');
      userDropdown?.classList.remove('open');
    });
  }

  // ── User dropdown ─────────────────────────────────────────
  const userBtn = document.getElementById('userBtn');
  const userDropdown = document.getElementById('userDropdown');

  if (userBtn && userDropdown) {
    userBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle('open');
      notifPanel?.classList.remove('open');
    });
  }

  // Close dropdowns on outside click
  document.addEventListener('click', () => {
    notifPanel?.classList.remove('open');
    userDropdown?.classList.remove('open');
  });

  // ── Mobile menu ───────────────────────────────────────────
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const navbarMenu = document.getElementById('navbarMenu');

  if (mobileBtn && navbarMenu) {
    mobileBtn.addEventListener('click', () => {
      navbarMenu.classList.toggle('open');
    });
  }

  // ── Password toggle ───────────────────────────────────────
  document.querySelectorAll('.password-toggle').forEach(btn => {
    btn.addEventListener('click', function() {
      const targetId = this.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      this.querySelector('i').className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
    });
  });

  // ── Auto-dismiss messages ─────────────────────────────────
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(alert => {
      alert.style.transition = 'opacity .4s ease, transform .4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(100%)';
      setTimeout(() => alert.remove(), 400);
    });
  }, 5000);

  // ── Mark notification read (navbar) ───────────────────────
  if (notifPanel) {
    notifPanel.querySelectorAll('.notif-item').forEach(item => {
      item.addEventListener('click', async function() {
        const id = this.dataset.id;
        if (!id || !this.classList.contains('unread')) return;
        try {
          await fetch(`/notifications/${id}/read/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
          });
          this.classList.remove('unread');
          updateNotifBadge(-1);
        } catch (e) { /* silent */ }
      });
    });
  }

  // ── Mark all read (navbar) ────────────────────────────────
  const markAllReadBtn = document.getElementById('markAllRead');
  if (markAllReadBtn) {
    markAllReadBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      try {
        await fetch('/notifications/mark-all-read/', {
          method: 'POST',
          headers: { 'X-CSRFToken': getCsrf() },
        });
        document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
        const badge = document.querySelector('.notif-badge');
        if (badge) badge.remove();
      } catch (e) { /* silent */ }
    });
  }

  function updateNotifBadge(delta) {
    const badge = document.querySelector('.notif-badge');
    if (!badge) return;
    const current = parseInt(badge.textContent) || 0;
    const next = current + delta;
    if (next <= 0) {
      badge.remove();
    } else {
      badge.textContent = next;
    }
  }

  function getCsrf() {
    return document.cookie.split('; ')
      .find(r => r.startsWith('csrftoken'))
      ?.split('=')[1] || '';
  }

  // ── Confirm dialogs for destructive actions ───────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });

  // ── Smooth scroll ─────────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // ── Poll unread notifications count (every 60s if logged in) ─
  if (document.querySelector('.notif-btn')) {
    setInterval(async () => {
      try {
        const res = await fetch('/notifications/unread-count/');
        const data = await res.json();
        const badge = document.querySelector('.notif-badge');
        if (data.count > 0) {
          if (badge) {
            badge.textContent = data.count;
          } else {
            const btn = document.querySelector('.notif-btn');
            if (btn) {
              const b = document.createElement('span');
              b.className = 'notif-badge';
              b.textContent = data.count;
              btn.appendChild(b);
            }
          }
        } else if (badge) {
          badge.remove();
        }
      } catch (e) { /* silent */ }
    }, 60000);
  }

  // ── eFootball Card 3D tilt effect ───────────────────────────
  document.querySelectorAll('.ef-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / (rect.width / 2);
      const dy = (e.clientY - cy) / (rect.height / 2);
      card.style.transform = `translateY(-16px) scale(1.06) rotateX(${-dy * 10}deg) rotateY(${dx * 10}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

});
