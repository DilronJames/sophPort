"""
Portfolio content for Dilpreet Singh.
Edit the values here to update the site. You don't need to touch the templates.
"""

BIO = {
    "name": "Dilpreet Singh",
    "first_name": "Dilpreet",
    "school": "Morris County School of Technology",
    "tagline": "Aspiring software engineer focused on cybersecurity and financial technology.",
    "career_track": "Cybersecurity & Software Engineering",
    "rotating_words": ["Cybersecurity", "Software Engineering", "FinTech", "Systems"],
    "summary": (
        "I am Dilpreet Singh, a student in the Computer and Information Sciences academy at the "
        "Morris County School of Technology. My focus is the intersection of cybersecurity and "
        "financial technology: building secure, reliable software and the tools used to analyze "
        "financial markets. I work primarily in Python, JavaScript, and C++, and I have designed "
        "and shipped both full-stack web applications and command-line programs. I have experience "
        "in collaborative team projects as well as independent, end-to-end development, and I hold "
        "my work to a standard of clean, well-documented, and defensible code. I am pursuing a "
        "career in software engineering with a concentration in security and financial systems."
    ),
    "interests": [
        {"name": "Cybersecurity",        "blurb": "Secure systems, threat modeling, and understanding how software fails."},
        {"name": "Financial Technology", "blurb": "Markets, trading strategies, and quantitative analysis."},
        {"name": "Software Engineering",  "blurb": "Clean architecture, testing, and shipping real, usable tools."},
        {"name": "3D Design & Printing",  "blurb": "Designing and 3D-printing functional parts and prototypes."},
    ],
    "skills": [
        "Python", "JavaScript", "Java", "C++",
        "HTML & CSS", "Flask", "pandas", "NumPy",
        "matplotlib", "yfinance", "p5.js", "Git & GitHub",
    ],
}

# These are working apps I built. You can actually use them on the site.
TOOLS = [
    {
        "slug": "backtester",
        "title": "Stock Strategy Backtester",
        "tagline": "A simple, theoretical test of the classic moving-average strategy. See if it would have beaten just buying and holding.",
        "url_endpoint": "backtest_page",
        "stack": ["Python", "Flask", "pandas", "NumPy", "matplotlib", "yfinance"],
        "highlights": [
            "A basic, textbook strategy (not trading advice)",
            "Plain-English summary of what happened",
            "Pick your own stock, dates, and settings",
        ],
        "preview_kind": "chart",
        "problem": (
            "Plenty of guides claim a trading strategy 'beats the market,' but rarely show the "
            "evidence. I wanted a tool that tests the classic moving-average crossover on real "
            "historical data and reports, in plain English, whether it would have outperformed "
            "simply buying and holding the stock."
        ),
        "process": (
            "I built the engine in Python first (backtest.py), which also runs as a command-line "
            "program. The core is intentionally small and testable: data is fetched with yfinance, "
            "trading signals are generated with pandas, and the simulation is all-in / all-out, "
            "executing each trade on the next day's open to avoid look-ahead bias. I then wrapped "
            "the engine in a Flask route that renders a three-panel matplotlib chart on the server "
            "and produces a plain-English narrative of the result."
        ),
        "challenges": (
            "The hardest parts were eliminating look-ahead bias (acting on a signal only on the "
            "following bar, never the same one), gracefully handling invalid tickers and missing "
            "market data, and translating finance metrics such as Sharpe ratio, Sortino ratio, and "
            "max drawdown into language a non-expert can actually understand."
        ),
        "source_url": "https://github.com/DilronJames",
    },
    {
        "slug": "password-strength",
        "title": "Password Strength Checker",
        "tagline": "See how strong a password really is. Everything runs in your browser, so nothing you type ever gets sent anywhere.",
        "url_endpoint": "password_page",
        "stack": ["Python", "JavaScript", "Shannon entropy"],
        "highlights": [
            "Scores how hard it is to guess",
            "Estimates how long it would take to crack",
            "Catches common patterns like 'qwerty' and '1234'",
        ],
        "preview_kind": "lock",
        "problem": (
            "Most password meters rely on brittle rules (one uppercase letter, one digit) that do "
            "not reflect how passwords are actually attacked. I wanted a checker that scores a "
            "password the way an attacker would, by estimating the size of the guess space, and "
            "that never transmits the password anywhere."
        ),
        "process": (
            "I wrote the scoring logic in Python first (password.py, which also runs as a CLI), "
            "using Shannon-entropy estimation, character-set detection, and common-pattern checks. "
            "I then mirrored that logic exactly in JavaScript so the entire analysis runs locally "
            "in the browser. The password is never sent to the server, which is the whole point."
        ),
        "challenges": (
            "Keeping the Python and JavaScript implementations in sync, modeling realistic "
            "crack-time estimates across four attacker speeds, and detecting weak patterns "
            "(sequences, repeats, keyboard walks, and dictionary words) without flagging strong "
            "passwords by mistake."
        ),
        "source_url": "https://github.com/DilronJames",
    },
]

CONTACT = {
    "email": "dilpreet.singh@mcvts.org",
    "github": "https://github.com/DilronJames",
    "github_alt": "",
    "linkedin": "",
    "location": "Morris County, New Jersey",
    # OPTIONAL: paste a free Web3Forms access key here to make the contact form
    # deliver messages straight to your inbox (no mail app needed on the visitor's
    # side). Get one in ~30 seconds at https://web3forms.com — enter your email,
    # they send you a key. Until this is set, the form falls back to opening the
    # visitor's mail app instead.
    "web3forms_key": "",
}

PROJECTS = [
    {
        "slug": "p5js-studio",
        "title": "p5.js Creative Coding Studio",
        "tagline": "Five interactive sketches exploring physics, color, noise, and motion in the browser.",
        "summary": (
            "A collection of five p5.js sketches built across freshman year, each isolating a different "
            "computational concept: 2D rolling physics, Perlin-noise color shifting, conditional and "
            "loop-driven color cycling on user input, Perlin-noise bubble fields, and vector-based "
            "motion with simulated gravity. Hosted in the p5.js web editor and embedded directly into "
            "my portfolio so visitors can interact with each piece in real time."
        ),
        "problem": (
            "Static screenshots don't communicate what an interactive program actually feels like. "
            "I needed a way to demonstrate motion, input handling, and procedural systems in a way "
            "a reader could click on and explore, not just read about."
        ),
        "stack": ["JavaScript", "p5.js", "HTML5 Canvas", "Web Editor (iframe embed)"],
        "concepts": ["Vectors & motion", "Perlin noise", "Conditionals", "Loops", "User input events", "Color theory"],
        "process": (
            "I started each sketch by writing the math on paper, especially for the gravity sketch, "
            "where I had to translate kinematic equations into per-frame velocity updates. "
            "Debugging visual programs is unusual: bugs don't crash, they just look wrong, so I "
            "leaned on print()-style debug overlays to inspect velocity vectors and noise values mid-run."
        ),
        "research_topic": (
            "Perlin noise as a way to generate organic, non-repeating motion. I looked into it on my "
            "own after I noticed that Math.random() looked too jittery and unnatural for the color and "
            "bubble sketches."
        ),
        "challenges": (
            "Getting the rolling-physics sketch to feel believable without a real physics engine took "
            "the most iteration. I had to tune the friction and bounce values by eye. "
            "On the gravity sketch, floating-point drift caused particles to slowly leak energy until I "
            "clamped velocity within a max bound."
        ),
        "v2": (
            "Rebuild the whole studio as a single-page app with a sketch picker, persistent settings, "
            "and shareable URLs that encode each sketch's parameters."
        ),
        "repo": "https://github.com/DilronJames/cis-academy-freshman-year-portfolio-DilronJames",
        "demo": "https://editor.p5js.org/dilpreet.singh/sketches",
        "image": "",
        "accent": "violet",
        "featured": True,
        "size": "lg",
        "tags": ["Web", "Creative Coding", "Featured"],
    },
    {
        "slug": "dreamdest",
        "title": "DreamDest",
        "tagline": "A travel-destination concept site demonstrating layout, typography, and visual hierarchy.",
        "summary": (
            "DreamDest is a multi-page web project I built to practice end-to-end front-end development "
            "outside of class assignments. It uses semantic HTML, custom CSS, and responsive layout "
            "techniques to present travel destinations with a clean editorial feel. The project pushed "
            "me past the 'one-page template' stage into thinking about navigation, content hierarchy, "
            "and reusable components."
        ),
        "problem": (
            "Most beginner web projects are single-page. I wanted to practice the parts of web "
            "development that scale: shared headers, consistent styling across pages, and content "
            "that reflows cleanly on mobile."
        ),
        "stack": ["HTML5", "CSS3", "Responsive design", "Flexbox / Grid"],
        "concepts": ["Semantic markup", "Mobile-first layout", "Visual hierarchy", "Typography"],
        "process": (
            "I sketched the home page first, then extracted a shared header/footer pattern before "
            "duplicating it across pages. That was a small but real step toward thinking like a "
            "component-based developer. Picking a consistent type scale and spacing taught me "
            "more than any tutorial did."
        ),
        "research_topic": (
            "CSS Grid and modern responsive patterns, specifically how to combine Grid for page "
            "structure with Flexbox for component-level alignment, which we didn't cover in class."
        ),
        "challenges": (
            "Cross-browser inconsistencies on Safari mobile, and getting images to scale without "
            "ruining the layout on small screens."
        ),
        "v2": (
            "Convert it into a real CMS-backed site or static-site generator (Astro, Eleventy) so I "
            "can publish new destinations without touching HTML."
        ),
        "repo": "https://github.com/DilronJames/DreamDest",
        "demo": "",
        "image": "",
        "accent": "teal",
        "featured": False,
        "size": "md",
        "tags": ["Web", "Front-End"],
    },
    {
        "slug": "mix-match",
        "title": "Mix-Match Website Challenge",
        "tagline": "Reverse-engineering a designer's mockup into clean, semantic HTML & CSS.",
        "summary": (
            "A web challenge where the goal was to match a given visual design pixel-for-pixel using "
            "only HTML and CSS. The constraint sharpened my eye for spacing, alignment, and the "
            "small typography choices that separate amateur layouts from professional ones."
        ),
        "problem": (
            "Designs in the real world come from designers, not developers. I needed to practice "
            "translating a finished visual into working code without being able to fall back on "
            "'just make it look okay'."
        ),
        "stack": ["HTML5", "CSS3", "Flexbox"],
        "concepts": ["Pixel-accurate layout", "Box model", "Spacing systems", "Color matching"],
        "process": (
            "I used browser DevTools to inspect element dimensions on the reference image, then "
            "built a CSS spacing scale (4 / 8 / 16 / 32px) before writing any layout code. This "
            "discipline-first approach saved me from the usual 'add margin until it looks right' trap."
        ),
        "research_topic": (
            "Design tokens, which means treating spacing, color, and type as a small set of reusable "
            "variables. It's how professional design systems are built."
        ),
        "challenges": (
            "Getting precise vertical rhythm across mixed font sizes, and reproducing subtle box-shadows "
            "that the design used heavily."
        ),
        "v2": (
            "Rebuild the same design in Tailwind CSS to compare it with hand-written CSS, and add a "
            "dark mode version."
        ),
        "repo": "https://github.com/DilronJames/Mix-Match-Website-Challenge",
        "demo": "",
        "image": "",
        "accent": "pink",
        "featured": False,
        "size": "md",
        "tags": ["Web", "Design"],
    },
]
