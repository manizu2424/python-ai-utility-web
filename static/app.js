const form = document.querySelector("#extract-form");
const fileInput = document.querySelector("#file-input");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const resultText = document.querySelector("#result-text");
const downloadLink = document.querySelector("#download-link");
const resetButton = document.querySelector("#reset-button");
const button = form.querySelector("button");
const pdfForm = document.querySelector("#pdf-form");
const pdfMode = document.querySelector("#pdf-mode");
const singleFileField = document.querySelector("#single-file-field");
const singleFileLabel = document.querySelector("#single-file-label");
const pdfFileInput = document.querySelector("#pdf-file-input");
const mergeFileField = document.querySelector("#merge-file-field");
const pdfMergeInput = document.querySelector("#pdf-merge-input");
const mergeFileSummary = document.querySelector("#merge-file-summary");
const mergeFileList = document.querySelector("#merge-file-list");
const clearMergeFilesButton = document.querySelector("#clear-merge-files");
const splitOptions = document.querySelector("#split-options");
const startPage = document.querySelector("#start-page");
const endPage = document.querySelector("#end-page");
const pdfMessage = document.querySelector("#pdf-message");
const pdfResult = document.querySelector("#pdf-result");
const pdfDownloadLink = document.querySelector("#pdf-download-link");
const pdfResetButton = document.querySelector("#pdf-reset-button");
const pdfButton = pdfForm.querySelector("button[type='submit']");
const menuItems = document.querySelectorAll(".menu-item");
const toolPanels = document.querySelectorAll(".tool-panel");
let mergeFiles = [];

menuItems.forEach((menuItem) => {
  menuItem.addEventListener("click", () => {
    const targetId = menuItem.dataset.target;

    menuItems.forEach((item) => {
      item.classList.toggle("active", item === menuItem);
    });

    toolPanels.forEach((panel) => {
      const isActive = panel.id === targetId;
      panel.hidden = !isActive;
      panel.classList.toggle("active", isActive);
    });
  });
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  setMessage(file ? `${file.name} 파일이 선택되었습니다.` : "", false);
});

pdfFileInput.addEventListener("change", () => {
  const file = pdfFileInput.files[0];
  setPdfMessage(file ? `${file.name} 파일이 선택되었습니다.` : "", false);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    setMessage("파일을 선택하세요.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  button.disabled = true;
  result.hidden = true;
  setMessage("처리 중입니다.", false);

  try {
    const response = await fetch("/api/extract-text", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();

    if (!response.ok) {
      setMessage(payload.detail || "텍스트 추출에 실패했습니다.", true);
      return;
    }

    resultText.value = payload.text || "";
    downloadLink.href = payload.download_url;
    result.hidden = false;
    setMessage(`${payload.filename} 처리 완료: ${payload.characters}자`, false);
  } catch {
    setMessage("서버 요청에 실패했습니다.", true);
  } finally {
    button.disabled = false;
  }
});

resetButton.addEventListener("click", () => {
  form.reset();
  resultText.value = "";
  downloadLink.href = "#";
  result.hidden = true;
  setMessage("", false);
  fileInput.focus();
});

pdfMode.addEventListener("change", () => {
  syncPdfMode();
});

pdfMergeInput.addEventListener("change", () => {
  addMergeFiles(pdfMergeInput.files);
});

mergeFileList.addEventListener("click", (event) => {
  const removeButton = event.target.closest("button[data-index]");
  if (!removeButton) {
    return;
  }

  mergeFiles.splice(Number(removeButton.dataset.index), 1);
  renderMergeFiles();
  syncMergeInputFiles();
});

clearMergeFilesButton.addEventListener("click", () => {
  resetMergeFiles();
  pdfMergeInput.focus();
});

function syncPdfMode() {
  const isMerge = pdfMode.value === "merge";
  const isSplit = pdfMode.value === "split";
  const isFromFile = pdfMode.value === "from-file";

  singleFileField.hidden = isMerge;
  mergeFileField.hidden = !isMerge;
  pdfFileInput.required = !isMerge;
  pdfMergeInput.required = false;
  pdfFileInput.value = "";
  pdfMergeInput.value = "";
  if (!isMerge) {
    resetMergeFiles();
  }
  mergeFileSummary.hidden = !isMerge || mergeFiles.length === 0;
  singleFileLabel.textContent = isFromFile ? "변환할 파일" : "PDF 파일";
  pdfFileInput.accept = isFromFile
    ? ".txt,.md,.docx,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
    : ".pdf";
  splitOptions.hidden = !isSplit;
  pdfResult.hidden = true;
  setPdfMessage("", false);
}

function addMergeFiles(fileList) {
  const nextFiles = Array.from(fileList);
  if (nextFiles.length === 0) {
    return;
  }

  const knownKeys = new Set(mergeFiles.map(getFileKey));
  for (const file of nextFiles) {
    if (getFileExtension(file.name) !== ".pdf") {
      continue;
    }

    const key = getFileKey(file);
    if (!knownKeys.has(key)) {
      mergeFiles.push(file);
      knownKeys.add(key);
    }
  }

  renderMergeFiles();
  syncMergeInputFiles();
  setPdfMessage(`${mergeFiles.length}개 PDF 파일이 선택되었습니다.`, false);
}

function renderMergeFiles() {
  mergeFileSummary.hidden = pdfMode.value !== "merge" || mergeFiles.length === 0;
  mergeFileList.replaceChildren();

  mergeFiles.forEach((file, index) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    const removeButton = document.createElement("button");

    name.textContent = `${index + 1}. ${file.name}`;
    removeButton.type = "button";
    removeButton.className = "secondary small";
    removeButton.dataset.index = String(index);
    removeButton.textContent = "삭제";

    item.append(name, removeButton);
    mergeFileList.append(item);
  });
}

function resetMergeFiles() {
  mergeFiles = [];
  pdfMergeInput.value = "";
  renderMergeFiles();
}

function syncMergeInputFiles() {
  if (typeof DataTransfer === "undefined") {
    return;
  }

  const transfer = new DataTransfer();
  mergeFiles.forEach((file) => transfer.items.add(file));
  try {
    pdfMergeInput.files = transfer.files;
  } catch {
    // 일부 브라우저는 보안 정책상 files 대입을 막을 수 있다.
  }
}

function getFileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function getFileExtension(filename) {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase();
}

pdfForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const isMerge = pdfMode.value === "merge";
  const files = isMerge ? mergeFiles : Array.from(pdfFileInput.files);
  if (files.length === 0) {
    setPdfMessage("파일을 선택하세요.", true);
    return;
  }
  if (isMerge && files.length < 2) {
    setPdfMessage("PDF 병합에는 파일이 2개 이상 필요합니다.", true);
    return;
  }

  const endpoint = `/api/pdf/${pdfMode.value}`;
  const formData = new FormData();

  if (isMerge) {
    files.forEach((file) => formData.append("files", file));
  } else {
    formData.append("file", files[0]);
  }

  if (pdfMode.value === "split") {
    formData.append("start_page", startPage.value);
    formData.append("end_page", endPage.value);
  }

  pdfButton.disabled = true;
  pdfResult.hidden = true;
  setPdfMessage("처리 중입니다.", false);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();

    if (!response.ok) {
      setPdfMessage(payload.detail || "PDF 변환에 실패했습니다.", true);
      return;
    }

    pdfDownloadLink.href = payload.download_url;
    pdfResult.hidden = false;
    setPdfMessage(payload.message || "PDF 변환이 완료되었습니다.", false);
  } catch {
    setPdfMessage("서버 요청에 실패했습니다.", true);
  } finally {
    pdfButton.disabled = false;
  }
});

pdfResetButton.addEventListener("click", () => {
  pdfForm.reset();
  resetMergeFiles();
  syncPdfMode();
  pdfDownloadLink.href = "#";
  pdfResult.hidden = true;
  setPdfMessage("", false);
  pdfMode.focus();
});

syncPdfMode();

function setMessage(text, isError) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setPdfMessage(text, isError) {
  pdfMessage.textContent = text;
  pdfMessage.classList.toggle("error", isError);
}
