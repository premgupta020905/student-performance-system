// DOM elements
const sign_in_btn = document.querySelector('#sign-in-btn');
const sign_up_btn = document.querySelector('#sign-up-btn');
const container = document.querySelector('.container');
const showPasswordCheckbox = document.querySelector('.show-password');
const passwordInput = document.getElementById('pwd');
const signInForm = document.querySelector('.sign-in-form');

// Toggle panels
sign_up_btn.addEventListener('click', () => {
  container.classList.add('sign-up-mode');
});

sign_in_btn.addEventListener('click', () => {
  container.classList.remove('sign-up-mode');
});

// Show / Hide password
if (showPasswordCheckbox && passwordInput) {
  showPasswordCheckbox.addEventListener('change', (e) => {
    passwordInput.type = e.target.checked ? 'text' : 'password';
  });
}

// Message box (TOP of form)
const messageBox = document.createElement("div");
messageBox.id = "login-message";
messageBox.style.color = "red";
messageBox.style.marginBottom = "10px";
signInForm.prepend(messageBox);

// Form validation
signInForm.addEventListener('submit', (e) => {
  const usernameInput = signInForm.querySelector('input[name="username"]');
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  // Both empty
  if (!username && !password) {
    e.preventDefault();
    messageBox.textContent = "⚠️ Please enter username and password";
    return;
  }

  // Only username
  if (username && !password) {
    e.preventDefault();
    messageBox.textContent = "⚠️ Please enter password";
    return;
  }

  // Only password
  if (!username && password) {
    e.preventDefault();
    messageBox.textContent = "⚠️ Please enter username";
    return;
  }

  // Valid → Django ko submit hone do
});

// Dynamic greeting
function dynamicGreeting() {
  const hour = new Date().getHours();
  let greeting = "Hello";

  if (hour < 12) greeting = "🌞 Good Morning!";
  else if (hour < 18) greeting = "🌤️ Good Afternoon!";
  else greeting = "🌙 Good Evening!";

  const title = document.querySelector('.sign-in-form .title');
  if (title) title.textContent = greeting;
}
dynamicGreeting();

// Accessibility
passwordInput.setAttribute("aria-label", "Password field");
showPasswordCheckbox.setAttribute("aria-label", "Show password checkbox");
