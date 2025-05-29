function toggleUserControls() {
  document.querySelector(".user-controls").classList.toggle("active");
}

function toggleNavMenu() {
  document.querySelector(".mobile-nav").classList.toggle("active");
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".toggle-password").forEach(function (button) {
    const passwordField = button
      .closest(".password-field")
      .querySelector("input[type='password'], input[type='text']");
    const icon = button.querySelector("img");

    button.addEventListener("click", function () {
      const isPassword = passwordField.getAttribute("type") === "password";
      passwordField.setAttribute("type", isPassword ? "text" : "password");

      icon.src = isPassword
        ? button.dataset.hideIcon
        : button.dataset.showIcon;

      icon.alt = isPassword ? "Hide password" : "Show password";
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const passwordInput = document.getElementById("password");

  const ruleLength = document.getElementById("rule-length");
  const ruleUppercase = document.getElementById("rule-uppercase");
  const ruleDigit = document.getElementById("rule-digit");

  const rules = [ruleLength, ruleUppercase, ruleDigit];

  passwordInput.addEventListener("input", function () {
    const value = passwordInput.value;

    if (value === "") {
      rules.forEach(rule => rule.className = "neutral");
      return;
    }

    ruleLength.className = value.length >= 8 ? "valid" : "invalid";
    ruleUppercase.className = /[\p{Lu}]/u.test(value) ? "valid" : "invalid";
    ruleDigit.className = /\d/.test(value) ? "valid" : "invalid";
  });

  passwordInput.addEventListener("focus", function () {
    if (passwordInput.value === "") {
      rules.forEach(rule => rule.className = "neutral");
    }
  });

  passwordInput.addEventListener("blur", function () {
    if (passwordInput.value === "") {
      rules.forEach(rule => rule.className = "neutral");
    }
  });
});



