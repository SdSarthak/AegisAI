const secretPatterns = [
  {
    name: "OpenAI API Key",
    regex: /sk-[a-zA-Z0-9]{20,}/g,
  },
  {
    name: "Email Address",
    regex: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
  },
  {
    name: "Phone Number",
    regex: /\b\d{10}\b/g,
  },
  {
    name: "AWS Access Key",
    regex: /AKIA[0-9A-Z]{16}/g,
  },
  {
    name: "JWT Token",
    regex: /eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+/g,
  },
];

function detectSecrets(text) {
  const detected = [];

  secretPatterns.forEach((pattern) => {
    if (pattern.regex.test(text)) {
      detected.push(pattern.name);
    }
  });

  return detected;
}

function showWarning(detectedItems) {
  let existingWarning = document.getElementById(
    "aegisai-secret-warning"
  );

  if (existingWarning) {
    existingWarning.remove();
  }

  const warningBox = document.createElement("div");
  warningBox.id = "aegisai-secret-warning";

  warningBox.innerHTML = `
    <strong>⚠ Sensitive Information Detected</strong><br>
    Detected:
    <ul>
      ${detectedItems.map((item) => `<li>${item}</li>`).join("")}
    </ul>
    Remove sensitive data before submitting your prompt.
  `;

  document.body.appendChild(warningBox);
}

function removeWarning() {
  const warning = document.getElementById(
    "aegisai-secret-warning"
  );

  if (warning) {
    warning.remove();
  }
}

document.addEventListener("input", (event) => {
  const target = event.target;

  if (
    target.tagName === "TEXTAREA" ||
    target.tagName === "INPUT"
  ) {
    const text = target.value;

    const detectedSecrets = detectSecrets(text);

    if (detectedSecrets.length > 0) {
      showWarning(detectedSecrets);
    } else {
      removeWarning();
    }
  }
});