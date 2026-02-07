const uploadBox = document.querySelector("#uploadBox");
const fileInput = document.querySelector("#fileInput");
const uploadButton = document.querySelector("#uploadButton");
const takePhotoButton = document.querySelector("#takePhotoButton");
const progressContainer = document.querySelector("#progressContainer");
const progressBar = document.querySelector("#progressBar");
const progressLabel = document.querySelector("#progressLabel");

const stages = [
  { label: "Scanning Invoice...", progress: 35 },
  { label: "Checking Manufacturer Data...", progress: 68 },
  { label: "Comparing Labor Rates...", progress: 100 },
];

let progressTimeouts = [];

const clearProgress = () => {
  progressTimeouts.forEach((timeout) => clearTimeout(timeout));
  progressTimeouts = [];
};

const startSimulation = () => {
  clearProgress();
  progressContainer.style.display = "block";
  progressBar.style.width = "0%";
  progressLabel.textContent = "Preparing scan...";

  stages.forEach((stage, index) => {
    const timeout = setTimeout(() => {
      progressBar.style.width = `${stage.progress}%`;
      progressLabel.textContent = stage.label;
    }, 600 * (index + 1));
    progressTimeouts.push(timeout);
  });

  const redirectTimeout = setTimeout(() => {
    window.location.href = "dashboard.html";
  }, 2000);
  progressTimeouts.push(redirectTimeout);
};

const handleFile = () => {
  startSimulation();
};

const openFilePicker = () => {
  fileInput.click();
};

uploadButton.addEventListener("click", openFilePicker);
takePhotoButton.addEventListener("click", openFilePicker);

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) {
    handleFile();
  }
});

uploadBox.addEventListener("dragover", (event) => {
  event.preventDefault();
  uploadBox.classList.add("upload-box--active");
});

uploadBox.addEventListener("dragleave", () => {
  uploadBox.classList.remove("upload-box--active");
});

uploadBox.addEventListener("drop", (event) => {
  event.preventDefault();
  uploadBox.classList.remove("upload-box--active");
  if (event.dataTransfer.files.length) {
    handleFile();
  }
});
