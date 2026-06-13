document.addEventListener('DOMContentLoaded', () => {
  
  // 1. STICKY NAVBAR
  const nav = document.getElementById('main-nav');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  });

  // 2. MOBILE MENU TOGGLE
  const menuToggle = document.getElementById('menu-toggle-btn');
  const navMenu = document.getElementById('nav-menu');
  
  if (menuToggle && navMenu) {
    menuToggle.addEventListener('click', () => {
      navMenu.classList.toggle('active');
      menuToggle.classList.toggle('open');
    });

    // Close menu when a link is clicked
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('active');
        menuToggle.classList.remove('open');
      });
    });
  }

  // 3. CARD SPOTLIGHT EFFECTS (Mouse Move Glow)
  document.querySelectorAll('.problem-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    });
  });

  // 4. ANIMATED STAT COUNTERS
  function animateCount(el) {
    if (el.dataset.animated) return;
    el.dataset.animated = "true";
    
    const target = parseFloat(el.getAttribute('data-target'));
    const isDecimal = target % 1 !== 0;
    const duration = 2000; // 2 seconds
    const startTime = performance.now();
    
    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease out quad formula: progress * (2 - progress)
      const easeProgress = progress * (2 - progress);
      const currentValue = easeProgress * target;
      
      if (isDecimal) {
        el.textContent = currentValue.toFixed(1);
      } else {
        el.textContent = Math.floor(currentValue).toLocaleString('en-IN');
      }
      
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        if (isDecimal) {
          el.textContent = target.toFixed(1);
        } else {
          el.textContent = target.toLocaleString('en-IN');
        }
      }
    }
    
    requestAnimationFrame(update);
  }

  // 5. SCROLL REVEAL OBSERVER
  const reveals = document.querySelectorAll('.reveal');
  const observerOptions = {
    root: null,
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px'
  };

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        
        // If stats grid is revealed, animate the counters inside
        const stats = entry.target.querySelectorAll('.count');
        stats.forEach(stat => animateCount(stat));
      }
    });
  }, observerOptions);

  reveals.forEach(el => revealObserver.observe(el));

  // 6. MODALS MANAGEMENT
  const modalCompany = document.getElementById('modal-company');
  const modalTruck = document.getElementById('modal-truck');
  const modalAuth = document.getElementById('modal-auth');

  // Trigger buttons
  const btnCompany = document.getElementById('cta-company-btn');
  const btnTruck = document.getElementById('cta-truck-btn');
  
  const btnLoginNav = document.getElementById('nav-login-btn');
  const btnLoginFooter = document.getElementById('footer-login-btn');
  const btnSignupNav = document.getElementById('nav-signup-btn');
  const btnSignupFooter = document.getElementById('footer-signup-btn');

  // Auth toggle settings
  const authTitle = document.getElementById('auth-modal-title');
  const authDesc = document.getElementById('auth-modal-desc');
  const authSubmit = document.getElementById('auth-submit-btn');
  const authNameGroup = document.getElementById('auth-group-name');
  const authToggleMsg = document.getElementById('auth-toggle-msg');
  const authToggleLink = document.getElementById('auth-toggle-link');

  // Helper open function
  function openModal(modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Lock background scrolling
  }

  // Helper close function
  function closeModal(modal) {
    modal.classList.remove('active');
    document.body.style.overflow = ''; // Unlock scrolling
  }

  // Bind trigger buttons to dedicated Auth Pages
  if (btnCompany) btnCompany.addEventListener('click', () => window.location.href = 'signup.html?role=company');
  if (btnTruck) btnTruck.addEventListener('click', () => window.location.href = 'signup.html?role=truck_owner');
  
  if (btnLoginNav) btnLoginNav.addEventListener('click', () => window.location.href = 'login.html');
  if (btnLoginFooter) btnLoginFooter.addEventListener('click', () => window.location.href = 'login.html');
  if (btnSignupNav) btnSignupNav.addEventListener('click', () => window.location.href = 'signup.html');
  if (btnSignupFooter) btnSignupFooter.addEventListener('click', () => window.location.href = 'signup.html');

  // Handle Auth switching state
  function showAuthModal(type) {
    if (type === 'signup') {
      authTitle.innerHTML = 'Create Transit<span>OS</span> Account';
      authDesc.textContent = 'Join India\'s first predictive B2B freight network.';
      authSubmit.textContent = 'Create Free Account';
      authNameGroup.style.display = 'block';
      authToggleMsg.textContent = 'Already have an account?';
      authToggleLink.textContent = 'Login';
    } else {
      authTitle.innerHTML = 'Login to Transit<span>OS</span>';
      authDesc.textContent = 'Secure access to India\'s freight intelligence engine.';
      authSubmit.textContent = 'Login';
      authNameGroup.style.display = 'none';
      authToggleMsg.textContent = 'Don\'t have an account?';
      authToggleLink.textContent = 'Sign Up';
    }
    openModal(modalAuth);
  }

  // Auth toggle link click
  if (authToggleLink) {
    authToggleLink.addEventListener('click', (e) => {
      e.preventDefault();
      const isLogin = authSubmit.textContent === 'Login';
      showAuthModal(isLogin ? 'signup' : 'login');
    });
  }

  // Close modals clicking outside or on close buttons
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal(modal);
      }
    });

    const closeBtn = modal.querySelector('.close-modal');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => closeModal(modal));
    }
  });

  // 7. FORM SUBMISSIONS SIMULATION
  function handleFormSubmit(formId, successMessage) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const content = form.parentElement;
      const originalHTML = content.innerHTML;

      // Render clean, beautiful inline notification success card
      content.innerHTML = `
        <div style="text-align: center; padding: 20px 0;">
          <div style="width: 64px; height: 64px; border-radius: 50%; background: rgba(255, 69, 0, 0.15); display: flex; align-items: center; justify-content: center; margin: 0 auto 24px auto;">
            <svg viewBox="0 0 24 24" fill="none" stroke="#FF4500" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="width: 28px; height: 28px;">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <h3 style="font-family: var(--font-header); font-size: 24px; font-weight: 800; margin-bottom: 12px; color: var(--text-white);">Request Received</h3>
          <p style="color: var(--text-muted); font-size: 14px; line-height: 1.6; margin-bottom: 30px; max-width: 340px; margin-left: auto; margin-right: auto;">
            ${successMessage}
          </p>
          <button class="btn btn-accent" id="modal-success-close" style="width: 100%;">Done</button>
        </div>
      `;

      const doneBtn = content.querySelector('#modal-success-close');
      doneBtn.addEventListener('click', () => {
        closeModal(content.closest('.modal-overlay'));
        // Restore form structure after fade closes
        setTimeout(() => {
          content.innerHTML = originalHTML;
          // Re-bind listeners after restoring HTML
          handleFormSubmit(formId, successMessage);
          // If it was auth modal, re-bind close button and toggle links
          const newClose = content.querySelector('.close-modal');
          if (newClose) {
            newClose.addEventListener('click', () => closeModal(content.closest('.modal-overlay')));
          }
          if (formId === 'auth-form') {
            const newToggle = content.querySelector('#auth-toggle-link');
            if (newToggle) {
              newToggle.addEventListener('click', (ev) => {
                ev.preventDefault();
                const isLogin = document.getElementById('auth-submit-btn').textContent === 'Login';
                showAuthModal(isLogin ? 'signup' : 'login');
              });
            }
          }
        }, 300);
      });
    });
  }

  handleFormSubmit('company-form', 'Success! Our logistics integration team will call you within 2 hours to review system onboarding.');
  handleFormSubmit('truck-form', 'Registration completed. You will receive SMS alerts for matching loads on your corridors within 24 hours.');
  handleFormSubmit('auth-form', 'Welcome back! Redirecting you securely to your TransitOS Control Dashboard...');

});
