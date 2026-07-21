/* ==========================================================================
   FAQ Chatbot - Frontend Logic
   ==========================================================================
   Organized into sections:
   1. DOM element references & state
   2. Utility functions (timestamps, scrolling, message rendering)
   3. Sending messages & talking to the Flask backend
   4. Suggested FAQs (loaded on page start)
   5. Dark / Light mode toggle
   6. Clear chat & Download chat as TXT
   7. Copy-to-clipboard & Text-to-Speech per bot message
   8. Event listeners & initial page load logic
   ========================================================================== */


/* --------------------------------------------------------------------
   1. DOM ELEMENT REFERENCES & STATE
   --------------------------------------------------------------------
   We grab references to every element we'll need to read from or
   write to, ONCE, at the top. Repeatedly calling document.getElementById
   inside functions works too, but grabbing them once here is cleaner
   and slightly faster.
-------------------------------------------------------------------- */
const appContainer = document.getElementById('appContainer');
const chatWindow = document.getElementById('chatWindow');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const suggestedFaqsContainer = document.getElementById('suggestedFaqs');
const themeToggleBtn = document.getElementById('themeToggleBtn');
const clearChatBtn = document.getElementById('clearChatBtn');
const downloadChatBtn = document.getElementById('downloadChatBtn');

// In-memory chat history, used to build the downloadable .txt transcript.
// Each entry: { sender: 'user' | 'bot', text: string, time: string }
// Why keep this separate from the DOM? Because scraping formatted text
// back OUT of HTML elements is messier than just storing plain data
// as we go, and appending to it, then using it whenever we need it.
let chatHistory = [];

// Tracks whichever SpeechSynthesisUtterance is currently speaking,
// so the "stop speaking" button knows what to cancel.
let currentUtterance = null;


/* --------------------------------------------------------------------
   2. UTILITY FUNCTIONS
-------------------------------------------------------------------- */

/**
 * Returns the current time formatted like "10:42 AM" for message timestamps.
 */
function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Scrolls the chat window to the bottom so the latest message is visible.
 * Called every time a new message is added.
 */
function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

/**
 * Creates and appends a chat bubble to the chat window.
 *
 * @param {string} sender - 'user' or 'bot'
 * @param {string} text - the message text to display
 *
 * Why one shared function for both user and bot messages?
 * Because the structure is 95% identical (avatar + bubble + timestamp).
 * We only branch behavior for the small differences (avatar icon,
 * and bot-only copy/speak buttons).
 */
function renderMessage(sender, text) {
    const time = getFormattedTime();

    // Save to history for the "download chat" feature, regardless of
    // how it's displayed.
    chatHistory.push({ sender, text, time });

    // Create the outer wrapper div: <div class="message bot">...</div>
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    // Avatar: a simple emoji inside a circle, kept lightweight (no images
    // required, avoids missing-image issues we saw earlier).
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = sender === 'user' ? '🧑' : '🤖';

    // Content wrapper holds the bubble + meta row (timestamp/actions)
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';
    bubbleDiv.textContent = text; // textContent (not innerHTML) avoids XSS risks from user input

    const metaDiv = document.createElement('div');
    metaDiv.className = 'message-meta';

    const timeSpan = document.createElement('span');
    timeSpan.textContent = time;
    metaDiv.appendChild(timeSpan);

    // Only bot messages get Copy + Speak buttons -- doesn't make sense
    // for the user to "hear" their own typed message read back.
    if (sender === 'bot') {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.textContent = '📋';
        copyBtn.title = 'Copy answer';
        copyBtn.onclick = () => copyToClipboard(text, copyBtn);

        const speakBtn = document.createElement('button');
        speakBtn.textContent = '🔊';
        speakBtn.title = 'Read aloud';
        speakBtn.onclick = () => speakText(text, speakBtn);

        actionsDiv.appendChild(copyBtn);
        actionsDiv.appendChild(speakBtn);
        metaDiv.appendChild(actionsDiv);
    }

    contentDiv.appendChild(bubbleDiv);
    contentDiv.appendChild(metaDiv);
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    chatWindow.appendChild(messageDiv);

    scrollToBottom();
}


/* --------------------------------------------------------------------
   3. SENDING MESSAGES & TALKING TO THE FLASK BACKEND
-------------------------------------------------------------------- */

/**
 * Shows the typing indicator (three bouncing dots).
 */
function showTypingIndicator() {
    typingIndicator.classList.remove('hidden');
    scrollToBottom();
}

/**
 * Hides the typing indicator.
 */
function hideTypingIndicator() {
    typingIndicator.classList.add('hidden');
}

/**
 * Sends the user's question to the Flask backend and displays the response.
 *
 * This function is `async` because fetch() is asynchronous -- it takes
 * time to get a response over the network, and we don't want to freeze
 * the browser while waiting. `await` pauses THIS function (not the whole
 * page) until each promise resolves, letting us write this top-to-bottom
 * instead of nesting .then() callbacks.
 */
async function sendMessage() {
    const question = userInput.value.trim();

    // Guard clause: don't send empty messages.
    if (!question) return;

    // Immediately show the user's message and clear the input box,
    // so the UI feels responsive even before the server replies.
    renderMessage('user', question);
    userInput.value = '';
    userInput.focus();

    showTypingIndicator();

    try {
        const response = await fetch('/get_answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question }),
        });

        // fetch() only rejects on network failure, NOT on HTTP error
        // codes like 400/500. We must check response.ok ourselves.
        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }

        const data = await response.json();
        hideTypingIndicator();
        renderMessage('bot', data.answer);

    } catch (error) {
        // Covers network failures (server down, no internet) AND
        // the manual throw above for bad HTTP status codes.
        console.error('Error contacting chatbot backend:', error);
        hideTypingIndicator();
        renderMessage('bot', "Sorry, I'm having trouble connecting right now. Please try again.");
    }
}


/* --------------------------------------------------------------------
   4. SUGGESTED FAQs (loaded once when the page starts)
-------------------------------------------------------------------- */

/**
 * Fetches all FAQ questions from /faqs and renders them as clickable
 * "chips". Clicking a chip auto-fills and sends that question --
 * a nice shortcut for users who don't know what to ask.
 */
async function loadSuggestedFaqs() {
    try {
        const response = await fetch('/faqs');
        if (!response.ok) throw new Error('Failed to load FAQs');

        const faqs = await response.json();

        // Show only a handful of suggestions (e.g. first 4) so the
        // header area doesn't get overwhelming -- full list is still
        // reachable by just asking naturally.
        const suggestions = faqs.slice(0, 4);

        suggestions.forEach(faq => {
            const chip = document.createElement('button');
            chip.className = 'faq-chip';
            chip.textContent = faq.question;
            chip.onclick = () => {
                userInput.value = faq.question;
                sendMessage();
            };
            suggestedFaqsContainer.appendChild(chip);
        });
    } catch (error) {
        console.error('Could not load suggested FAQs:', error);
        // Fail silently in the UI -- suggested FAQs are a nice-to-have,
        // not critical, so we don't want to show a scary error for this.
    }
}


/* --------------------------------------------------------------------
   5. DARK / LIGHT MODE TOGGLE
-------------------------------------------------------------------- */

/**
 * Applies a theme ('light' or 'dark') to the page and remembers it
 * in localStorage so it persists across page reloads.
 */
function applyTheme(theme) {
    appContainer.setAttribute('data-theme', theme);
    themeToggleBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
    localStorage.setItem('chatbot-theme', theme);
}

function toggleTheme() {
    const currentTheme = appContainer.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
}


/* --------------------------------------------------------------------
   6. CLEAR CHAT & DOWNLOAD CHAT AS TXT
-------------------------------------------------------------------- */

/**
 * Clears all messages from the chat window and resets history,
 * then shows the welcome message again.
 */
function clearChat() {
    const confirmed = confirm('Are you sure you want to clear the chat?');
    if (!confirmed) return;

    chatWindow.innerHTML = '';
    chatHistory = [];
    showWelcomeMessage();
}

/**
 * Builds a plain-text transcript from chatHistory and triggers a
 * browser download as a .txt file.
 */
function downloadChat() {
    if (chatHistory.length === 0) {
        alert('No chat messages to download yet.');
        return;
    }

    // Build a readable plain-text version of the conversation.
    const lines = chatHistory.map(entry => {
        const label = entry.sender === 'user' ? 'You' : 'Bot';
        return `[${entry.time}] ${label}: ${entry.text}`;
    });
    const textContent = lines.join('\n');

    // Create a Blob (a file-like object in memory) and a temporary
    // download link, click it programmatically, then clean up.
    // This is the standard vanilla-JS pattern for client-side file downloads.
    const blob = new Blob([textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `faq-chat-${Date.now()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url); // free up memory
}


/* --------------------------------------------------------------------
   7. COPY-TO-CLIPBOARD & TEXT-TO-SPEECH
-------------------------------------------------------------------- */

/**
 * Copies the given text to the clipboard and gives brief visual
 * feedback on the button that was clicked.
 */
function copyToClipboard(text, buttonEl) {
    navigator.clipboard.writeText(text).then(() => {
        const original = buttonEl.textContent;
        buttonEl.textContent = '✅';
        setTimeout(() => { buttonEl.textContent = original; }, 1200);
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

/**
 * Reads the given text aloud using the browser's built-in
 * SpeechSynthesis API (no external service or API key needed).
 */
function speakText(text, buttonEl) {
    // If something is already being spoken, stop it first --
    // avoids overlapping voices if the user clicks multiple speak buttons.
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }

    currentUtterance = new SpeechSynthesisUtterance(text);
    currentUtterance.rate = 1;
    currentUtterance.pitch = 1;

    // Swap the button to a "stop" icon while speaking, so the user
    // has an obvious way to stop the speech mid-sentence.
    buttonEl.textContent = '⏹️';
    currentUtterance.onend = () => { buttonEl.textContent = '🔊'; };

    window.speechSynthesis.speak(currentUtterance);

    // Clicking the same button again while speaking stops it
    // (re-assign onclick to a stop action for the duration of speech).
    buttonEl.onclick = () => {
        window.speechSynthesis.cancel();
        buttonEl.textContent = '🔊';
        buttonEl.onclick = () => speakText(text, buttonEl);
    };
}


/* --------------------------------------------------------------------
   8. EVENT LISTENERS & INITIAL PAGE LOAD
-------------------------------------------------------------------- */

/**
 * Shows a friendly welcome message from the bot -- called on first
 * load and again after clearing the chat.
 */
function showWelcomeMessage() {
    renderMessage('bot', "Hi! 👋 I'm your FAQ Assistant. Ask me anything, or tap a suggestion below to get started.");
}

// Send message when the Send button is clicked.
sendBtn.addEventListener('click', sendMessage);

// Send message when the user presses Enter inside the input box.
userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

themeToggleBtn.addEventListener('click', toggleTheme);
clearChatBtn.addEventListener('click', clearChat);
downloadChatBtn.addEventListener('click', downloadChat);

// ---- Runs once when the page first loads ----
(function initApp() {
    // Restore the user's last theme choice, defaulting to 'light'
    // if they've never visited before (localStorage returns null).
    const savedTheme = localStorage.getItem('chatbot-theme') || 'light';
    applyTheme(savedTheme);

    showWelcomeMessage();
    loadSuggestedFaqs();
})();