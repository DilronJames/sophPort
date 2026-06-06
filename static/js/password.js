/* ============================================================
   Password strength analyzer, client-side.
   Mirrors password.py so the same logic runs locally in the
   browser. Passwords are NEVER sent to the server.
   ============================================================ */

const CHARSET = {
    lower: 26, upper: 26, digits: 10,
    symbols: 33, spaces: 1, extended: 100,
};

const SPEEDS = [
    ['Throttled online',   '10 guesses / sec',         10],
    ['Fast online API',    '1,000 guesses / sec',      1e3],
    ['Slow offline hash',  '1M guesses / sec',         1e6],
    ['Offline GPU farm',   '10B guesses / sec',        1e10],
];

const COMMON = new Set([
    'password','passw0rd','p@ssw0rd','p@ssword',
    '123456','12345678','123456789','qwerty','qwertyuiop',
    'letmein','iloveyou','admin','welcome','monkey',
    'dragon','abc123','111111','000000','1q2w3e4r',
    'trustno1','sunshine','princess','football','starwars',
    'superman','batman','master','ninja','shadow',
    'michael','andrew','joshua','matthew',
]);

const KB_ROWS = [
    'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
    '1234567890',
    'qazwsxedcrfvtgbyhnujmikolp',
];

const LABELS = [
    { name: 'Critical', min: 0,  color: '#ef4444' },
    { name: 'Weak',     min: 28, color: '#f97316' },
    { name: 'Fair',     min: 40, color: '#eab308' },
    { name: 'Strong',   min: 60, color: '#22c55e' },
    { name: 'Vault',    min: 80, color: '#16ff65' },
];

function detectCharset(pw) {
    const used = []; let size = 0;
    if (/[a-z]/.test(pw)) { used.push('lowercase'); size += CHARSET.lower; }
    if (/[A-Z]/.test(pw)) { used.push('uppercase'); size += CHARSET.upper; }
    if (/\d/.test(pw))    { used.push('digits');    size += CHARSET.digits; }
    if (/[!-/:-@\[-`{-~]/.test(pw)) { used.push('symbols'); size += CHARSET.symbols; }
    if (pw.includes(' ')) { used.push('spaces');    size += CHARSET.spaces; }
    if (/[^\x20-\x7e]/.test(pw)) { used.push('extended'); size += CHARSET.extended; }
    return { size: Math.max(size, 1), used };
}

function hasSequentialRun(pw, n = 4) {
    pw = pw.toLowerCase();
    for (let i = 0; i <= pw.length - n; i++) {
        let ok = true;
        for (let j = 0; j < n - 1; j++) {
            if (pw.charCodeAt(i + j + 1) - pw.charCodeAt(i + j) !== 1) { ok = false; break; }
        }
        if (ok) return true;
    }
    return false;
}
function hasRepeatRun(pw, n = 3) {
    const re = new RegExp(`(.)\\1{${n - 1},}`);
    return re.test(pw);
}
function hasKeyboardWalk(pw, n = 4) {
    const l = pw.toLowerCase();
    return KB_ROWS.some(row => {
        for (let i = 0; i <= row.length - n; i++) {
            if (l.includes(row.substr(i, n))) return true;
        }
        return false;
    });
}
function isYear(pw) { return /^(19|20)\d{2}$/.test(pw); }
function isCommon(pw) { return COMMON.has(pw.toLowerCase()); }

function humanize(seconds) {
    if (seconds < 1) return 'instant';
    if (seconds < 60) return `${Math.round(seconds)} sec`;
    if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} hours`;
    if (seconds < 31536000) return `${Math.round(seconds / 86400)} days`;
    const years = seconds / 31536000;
    if (years < 1e3) return `${Math.round(years).toLocaleString()} years`;
    if (years < 1e6) return `${Math.round(years / 1e3).toLocaleString()}K years`;
    if (years < 1e9) return `${Math.round(years / 1e6).toLocaleString()}M years`;
    if (years < 1e12) return `${Math.round(years / 1e9).toLocaleString()}B years`;
    return 'heat-death of the universe';
}

export function analyze(pw) {
    const length = pw.length;
    const { size: charsetSize, used } = detectCharset(pw);
    const rawBits = length > 0 ? length * Math.log2(charsetSize) : 0;

    const issues = [];
    const suggestions = [];
    let penalty = 0;

    if (length === 0) {
        issues.push('Empty.');
        suggestions.push('Type a password to get a score.');
    }
    if (length > 0 && length < 8) {
        issues.push('Shorter than 8 characters.');
        suggestions.push('Add length - every extra character roughly doubles the cost.');
    }
    if (length >= 8 && length < 12) {
        suggestions.push('Aim for 14+ characters for online-attack resistance.');
    }
    if (length > 0 && isCommon(pw))      { issues.push('On every cracker\'s first-pass list.'); penalty += 40; }
    if (length > 0 && hasSequentialRun(pw)) { issues.push('Sequential run (abcd / 1234).');     penalty += 12; }
    if (length > 0 && hasRepeatRun(pw))     { issues.push('Repeating-character run.');           penalty += 10; }
    if (length > 0 && hasKeyboardWalk(pw))  { issues.push('Adjacent-key walk (qwerty / asdf).'); penalty += 12; }
    if (length > 0 && isYear(pw))           { issues.push('Just a year - guessed in seconds.'); penalty += 25; }
    if (length > 0 && used.length === 1)    { suggestions.push('Mix in at least one other character class.'); }
    if (length > 0 && !used.includes('symbols')) { suggestions.push('Add a symbol - it triples the alphabet.'); }

    const effectiveBits = Math.max(rawBits - penalty, 0);
    const score = Math.max(0, Math.min(100, Math.round(effectiveBits / 80 * 100)));

    let label = LABELS[0];
    for (const L of LABELS) if (effectiveBits >= L.min) label = L;

    const guesses = Math.pow(2, effectiveBits) / 2;
    const crackTimes = SPEEDS.map(([name, rate, gps]) => ({
        name, rate, time: humanize(guesses / gps),
    }));

    return {
        length,
        charsetSize,
        charsetsUsed: used,
        rawBits,
        effectiveBits,
        strengthLabel: label.name,
        strengthColor: label.color,
        score,
        crackTimes,
        issues,
        suggestions,
    };
}

/* ============================================================
   Wiring
   ============================================================ */
(function wire() {
    const input  = document.getElementById('pwInput');
    if (!input) return;

    const meter   = document.getElementById('pwMeterFill');
    const label   = document.getElementById('pwLabel');
    const bits    = document.getElementById('pwBits');
    const charset = document.getElementById('pwCharset');
    const length  = document.getElementById('pwLength');
    const alpha   = document.getElementById('pwAlpha');
    const tbody   = document.getElementById('pwCrackBody');
    const issues  = document.getElementById('pwIssues');
    const sug     = document.getElementById('pwSuggestions');
    const toggle  = document.getElementById('pwToggle');
    const sample  = document.getElementById('pwSamples');

    function render(r) {
        meter.style.width = r.score + '%';
        meter.style.background = r.strengthColor;
        label.textContent = r.strengthLabel;
        label.style.color = r.strengthColor;
        bits.textContent = r.effectiveBits.toFixed(1);
        length.textContent = r.length;
        alpha.textContent = r.charsetSize;
        charset.innerHTML = r.charsetsUsed.length
            ? r.charsetsUsed.map(c => `<span class="pw-tag">${c}</span>`).join('')
            : '<span class="pw-tag pw-tag-empty">none</span>';
        tbody.innerHTML = r.crackTimes.map(c => `
            <tr>
                <td>${c.name}</td>
                <td class="pw-mute">${c.rate}</td>
                <td><strong>${c.time}</strong></td>
            </tr>`).join('');
        issues.innerHTML = r.issues.length
            ? r.issues.map(i => `<li class="pw-issue">${i}</li>`).join('')
            : '<li class="pw-ok">No red-flag patterns detected.</li>';
        sug.innerHTML = r.suggestions.length
            ? r.suggestions.map(s => `<li>${s}</li>`).join('')
            : '<li class="pw-mute">Nothing to improve.</li>';
    }

    function run() { render(analyze(input.value)); }

    input.addEventListener('input', run);

    toggle?.addEventListener('click', () => {
        const showing = input.type === 'text';
        input.type = showing ? 'password' : 'text';
        toggle.textContent = showing ? 'Show' : 'Hide';
    });

    sample?.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-sample]');
        if (!btn) return;
        input.value = btn.dataset.sample;
        input.type = 'text';
        if (toggle) toggle.textContent = 'Hide';
        run();
        input.focus();
    });

    run();
})();
