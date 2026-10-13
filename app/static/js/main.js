// Global JavaScript for Wardrobe IQ
document.addEventListener('DOMContentLoaded', () => {
  // Mobile sidebar toggle
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('appSidebar');
  if (mobileBtn && sidebar) {
    mobileBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Floating Chatbot toggle
  const toggleChatBtn = document.getElementById('toggleChatbotBtn');
  const closeChatBtn = document.getElementById('closeChatbotBtn');
  const chatbotWindow = document.getElementById('chatbotWindow');

  if (toggleChatBtn && chatbotWindow) {
    toggleChatBtn.addEventListener('click', () => {
      chatbotWindow.classList.toggle('open');
      if (chatbotWindow.classList.contains('open')) {
        document.getElementById('chatInput')?.focus();
      }
    });
  }

  if (closeChatBtn && chatbotWindow) {
    closeChatBtn.addEventListener('click', () => {
      chatbotWindow.classList.remove('open');
    });
  }
});

// Helper for quick chat suggestions
function sendQuickPrompt(promptText) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = promptText;
    const form = document.getElementById('chatbotForm');
    if (form) {
      form.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  }
}

// Chatbot markdown & list formatter
function formatStylistResponse(text) {
  if (!text) return '';
  // If text is an HTML component like ai-config-notice, return directly
  if (text.includes('<div class="ai-config-notice">') || text.includes('<div class="ai-stylist-status-notice">')) {
    return text;
  }
  let formatted = text;
  // Markdown bold **text** -> <strong>text</strong>
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Markdown italic *text* -> <em>$1</em>
  formatted = formatted.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

  const lines = formatted.split('\n');
  let inList = false;
  let result = [];
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) {
        result.push('<ul class="chat-bullet-list">');
        inList = true;
      }
      const itemContent = trimmed.replace(/^([•\-\*]\s*)/, '').trim();
      result.push(`<li>${itemContent}</li>`);
    } else {
      if (inList) {
        result.push('</ul>');
        inList = false;
      }
      if (trimmed.length > 0) {
        result.push(`<p>${trimmed}</p>`);
      }
    }
  }
  if (inList) {
    result.push('</ul>');
  }
  return result.join('');
}

// Reset Chatbot Conversation
async function resetChatConversation() {
  const messagesBox = document.getElementById('chatMessages');
  if (!messagesBox) return;
  try {
    await fetch('/api/chatbot/reset', { method: 'POST' });
  } catch (err) {
    console.warn("Failed to reset chat:", err);
  }
  messagesBox.innerHTML = `
    <div class="chat-bubble bot">
      Hello! Conversation cleared. I'm your personal AI stylist for Wardrobe IQ. You can ask me <em>any</em> open-ended styling question about your pieces, occasion looks, 2026 trends, capsule packing, or silhouette advice!
    </div>
    <div class="chat-suggestions">
      <button class="chat-tag-btn" onclick="sendQuickPrompt('What should I wear to my cousin\\'s engagement?')">Cousin's engagement</button>
      <button class="chat-tag-btn" onclick="sendQuickPrompt('I have a black shirt. What can I pair it with?')">Pair black shirt</button>
      <button class="chat-tag-btn" onclick="sendQuickPrompt('How can I make my outfit look more elegant?')">More elegant styling</button>
      <button class="chat-tag-btn" onclick="sendQuickPrompt('What fashion colours are trending this season?')">2026 Trend colours</button>
      <button class="chat-tag-btn" onclick="sendQuickPrompt('I am travelling for three days. Help me plan outfits.')">3-day travel plan</button>
      <button class="chat-tag-btn" onclick="sendQuickPrompt('Why does this outfit combination work?')">Why outfits work</button>
    </div>
  `;
  const input = document.getElementById('chatInput');
  if (input) input.value = '';
}

// Chatbot form submit
async function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById('chatInput');
  const messagesBox = document.getElementById('chatMessages');
  const form = document.getElementById('chatbotForm');
  const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
  if (!input || !messagesBox) return;

  const query = input.value.trim();
  if (!query) return;

  // Append user message
  const userBubble = document.createElement('div');
  userBubble.className = 'chat-bubble user';
  userBubble.textContent = query;
  messagesBox.appendChild(userBubble);
  input.value = '';
  if (submitBtn) submitBtn.disabled = true;
  messagesBox.scrollTop = messagesBox.scrollHeight;

  // Append loading indicator
  const botLoading = document.createElement('div');
  botLoading.className = 'chat-bubble bot loading-bubble';
  botLoading.innerHTML = '<em><span class="chat-spinner"></span> Styling with your actual closet & 2026 trends...</em>';
  messagesBox.appendChild(botLoading);
  messagesBox.scrollTop = messagesBox.scrollHeight;

  try {
    const res = await fetch('/api/chatbot/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query })
    });
    const data = await res.json();
    botLoading.classList.remove('loading-bubble');
    if (data && data.reply) {
      botLoading.innerHTML = formatStylistResponse(data.reply);
    } else {
      botLoading.innerHTML = "I couldn't process that query right now.";
    }
  } catch (err) {
    botLoading.classList.remove('loading-bubble');
    botLoading.innerHTML = '<span style="color:#d9534f;">Unable to connect to the styling service. Please check your network connection and try again.</span>';
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    messagesBox.scrollTop = messagesBox.scrollHeight;
  }
}
