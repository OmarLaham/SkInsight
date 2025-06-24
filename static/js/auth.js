const signInTab = document.getElementById('signInTab');
const signUpTab = document.getElementById('signUpTab');
const signInContent = document.getElementById('signInContent');
const signUpContent = document.getElementById('signUpContent');
const switchToSignUp = document.getElementById('switchToSignUp');
const switchToSignIn = document.getElementById('switchToSignIn');

signInTab.addEventListener('click', () => {
  signInContent.classList.remove('hidden');
  signUpContent.classList.add('hidden');
  signInTab.classList.add('font-bold', 'text-pink-600', 'border-b-2', 'border-pink-600');
  signUpTab.classList.remove('font-bold', 'text-pink-600', 'border-b-2', 'border-pink-600');
});

signUpTab.addEventListener('click', () => {
  signUpContent.classList.remove('hidden');
  signInContent.classList.add('hidden');
  signUpTab.classList.add('font-bold', 'text-pink-600', 'border-b-2', 'border-pink-600');
  signInTab.classList.remove('font-bold', 'text-pink-600', 'border-b-2', 'border-pink-600');
});

switchToSignUp.addEventListener('click', (e) => {
  e.preventDefault();
  signUpTab.click();
});

switchToSignIn.addEventListener('click', (e) => {
  e.preventDefault();
  signInTab.click();
});

function loginWithGoogle() {
  //window.location.href = 'https://your-backend.com/auth/google';
}

function loginWithFacebook() {
  //window.location.href = 'https://your-backend.com/auth/facebook';
}
