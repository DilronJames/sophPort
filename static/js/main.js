/* Theme toggle, dark is default, light is opt-in */
(function themeToggle() {
    const btn = document.getElementById('themeToggle');
    const root = document.documentElement;
    if (!btn) return;
    btn.addEventListener('click', () => {
        const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem('theme', next); } catch (e) {}
    });
})();

/* ============================================================
   Sports cursor: cycles through sport icons on every click.
   Order: basketball, soccer, football, tennis, boxing gloves.
   The position is remembered across pages via sessionStorage.
   ============================================================ */
(function sportsCursor() {
    // Each icon sits on a 32x32 canvas, centred at (15,15), radius ~12. Layers,
    // back to front: a soft dark drop shadow (depth on light backgrounds), a soft
    // white outer glow + a solid bright white halo ring (the "highlight" that keeps
    // the cursor visible on the dark theme), then the icon itself.
    const svgs = [
        // basketball
        `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32"><circle cx="16.5" cy="17" r="12.5" fill="#000" opacity="0.35"/><circle cx="15" cy="15" r="14.6" fill="#fff" opacity="0.4"/><circle cx="15" cy="15" r="13.7" fill="#fff"/><circle cx="15" cy="15" r="12" fill="#e8852b" stroke="#141414" stroke-width="1.5"/><path d="M3 15H27M15 3V27M7 6Q15 15 7 24M23 6Q15 15 23 24" fill="none" stroke="#141414" stroke-width="1.4"/></svg>`,
        // soccer ball
        `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32"><circle cx="16.5" cy="17" r="12.5" fill="#000" opacity="0.35"/><circle cx="15" cy="15" r="14.6" fill="#fff" opacity="0.4"/><circle cx="15" cy="15" r="13.7" fill="#fff"/><circle cx="15" cy="15" r="12" fill="#f8f8f8" stroke="#141414" stroke-width="1.5"/><polygon points="15,9 19.5,12.5 17.8,18 12.2,18 10.5,12.5" fill="#141414"/><path d="M15 3.4V7M5.5 11l3.4 2.4M24.5 11l-3.4 2.4M9.3 25l2.1-4.5M20.7 25l-2.1-4.5" stroke="#141414" stroke-width="1.3" fill="none"/></svg>`,
        // football (american)
        `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32"><ellipse cx="16.5" cy="17" rx="12.5" ry="8" fill="#000" opacity="0.35"/><ellipse cx="15" cy="15" rx="14.6" ry="10" fill="#fff" opacity="0.4"/><ellipse cx="15" cy="15" rx="13.7" ry="9.2" fill="#fff"/><ellipse cx="15" cy="15" rx="12" ry="7.6" fill="#7a4a24" stroke="#141414" stroke-width="1.5"/><path d="M15 10v10M11.5 12.5h7M11.5 15h7M11.5 17.5h7" stroke="#f5f5f5" stroke-width="1.5" fill="none"/></svg>`,
        // tennis ball
        `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32"><circle cx="16.5" cy="17" r="12.5" fill="#000" opacity="0.35"/><circle cx="15" cy="15" r="14.6" fill="#fff" opacity="0.4"/><circle cx="15" cy="15" r="13.7" fill="#fff"/><circle cx="15" cy="15" r="12" fill="#cfe84b" stroke="#141414" stroke-width="1.5"/><path d="M5 7Q14 15 5 23M25 7Q16 15 25 23" fill="none" stroke="#3a3a1a" stroke-width="1.5"/></svg>`,
        // boxing glove
        `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 32 32"><g transform="translate(1.5,2)" fill="#000" opacity="0.35"><path d="M10 5Q22 5 22 15L22 19Q22 22 19 22L11 22Q9 22 9 20L9 8Q9 5 10 5Z"/><path d="M9 11Q4 11 5 15Q6 18 9 17Z"/><rect x="9" y="22" width="13" height="4.3" rx="1.6"/></g><g fill="none" stroke="#fff" stroke-width="5" opacity="0.4" stroke-linejoin="round"><path d="M10 5Q22 5 22 15L22 19Q22 22 19 22L11 22Q9 22 9 20L9 8Q9 5 10 5Z"/><path d="M9 11Q4 11 5 15Q6 18 9 17Z"/></g><g fill="#fff" stroke="#fff" stroke-width="3.4" stroke-linejoin="round"><path d="M10 5Q22 5 22 15L22 19Q22 22 19 22L11 22Q9 22 9 20L9 8Q9 5 10 5Z"/><path d="M9 11Q4 11 5 15Q6 18 9 17Z"/></g><path d="M10 5Q22 5 22 15L22 19Q22 22 19 22L11 22Q9 22 9 20L9 8Q9 5 10 5Z" fill="#d62828" stroke="#141414" stroke-width="1.4"/><path d="M9 11Q4 11 5 15Q6 18 9 17Z" fill="#d62828" stroke="#141414" stroke-width="1.4"/><rect x="9" y="22" width="13" height="4.3" rx="1.6" fill="#f5f5f5" stroke="#141414" stroke-width="1.3"/></svg>`,
    ];

    const cursors = svgs.map(
        s => `url("data:image/svg+xml,${encodeURIComponent(s)}") 14 14, auto`
    );

    let i = 0;
    try {
        const saved = parseInt(sessionStorage.getItem('sportCursor'), 10);
        if (!Number.isNaN(saved)) i = ((saved % cursors.length) + cursors.length) % cursors.length;
    } catch (e) {}

    function apply() { document.documentElement.style.cursor = cursors[i]; }
    apply();

    document.addEventListener('click', () => {
        i = (i + 1) % cursors.length;
        apply();
        try { sessionStorage.setItem('sportCursor', String(i)); } catch (e) {}
    });
})();

/* Console signature */
(function () {
    console.log('%c Built by Dilpreet Singh, github.com/DilronJames ',
                'background:#5a9e72;color:#0a0a0a;padding:6px 10px;font-family:monospace');
})();
