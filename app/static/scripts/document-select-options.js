const documentStates = new Map();
  let selectedDocument = null;

  let digest_algorithm = null;
  function saveDigestAlgorithm(value) {
    digest_algorithm = value;
  }

  const DEFAULT_OPTIONS = {
    container: "No",
    signature_format: null,
    packaging: null,
    level: "Ades-B-B",
    confirmed: false,
    file: null,
    fileURL: null,
    fileType: null,
  };
  function saveOption(groupName, value) {
    if (!selectedDocument) return;
    const state = documentStates.get(selectedDocument);
    if (state) state[groupName] = value;
  }

  function updateDocumentsList(filename, filetype, file) {
    if (!file) return;

	documentStates.clear();
	document.getElementById("item-list").innerHTML = "";

    let fileURL;
    if (filetype === "application/pdf") {
      fileURL = URL.createObjectURL(
        new Blob([file], { type: "application/pdf" }),
      );
    } else {
      fileURL = URL.createObjectURL(file);
    }
    documentStates.set(filename, {
      ...DEFAULT_OPTIONS,
      file: null,
      fileURL,
      fileType: filetype,
    });

    const itemList = document.getElementById("item-list");
    const li = document.createElement("li");
    li.className = "document-list-item";
    li.dataName = filename;
    li.dataset.name = filename;
    li.innerHTML = `
        <div class="document-list-item-name">
          <i class="fa-regular fa-file"></i>
          <span class="item-name">${filename}</span>
        </div>
        <div class="document-list-item-options">
          <span class="status-badge pending">Options needed</span>
          <button class="btn common-btn secondary-btn icon-btn" onclick="removeItem(this)">✕</button>
        </div>
    `;
    li.addEventListener("click", (e) => {
      if (e.target.classList.contains("icon-btn")) return;
      selectDocument(filename);
    });
    itemList.appendChild(li);

    document.getElementById("signature-options").hidden = false;
    document.getElementById("submit-btn-container").hidden = true;
    selectDocument(filename);
  }

  function removeItem(button) {
    const li = button.closest(".document-list-item");
    const filename = li.dataset.name;

    documentStates.delete(filename);
    li.remove();

    const itemList = document.getElementById("item-list");
    if (itemList.children.length === 0) {
      document.getElementById("signature-options").hidden = true;
      document.getElementById("submit-btn-container").hidden = true;
      selectedDocument = null;
      return;
    }
    if (selectedDocument === filename) {
      const firstRemaining = itemList.children[0].dataset.name;
      selectDocument(firstRemaining);
    }

    document.getElementById("submit-btn-container").hidden =
      !checkAllConfirmed();
  }

  function selectDocument(filename) {
    // removes all other selected documents
    document
      .querySelectorAll(".document-list-item")
      .forEach((el) => el.classList.remove("selected"));
    // 'selects' the document to change css
    const el = document.querySelector(`[data-name="${CSS.escape(filename)}"]`);
    if (el) el.classList.add("selected");

    selectedDocument = filename;
    document.getElementById("selected-document-name").innerText = filename;

    const state = documentStates.get(filename);
    loadOptionsPanel(state);

    lockOptionsPanel(state.confirmed === true);
    document.getElementById("signature-options").hidden = false;
  }

  function loadOptionsPanel(state) {
    setRadio("container", state.container);
    setRadio("signature_format", state.signature_format);
    setRadio("packaging", state.packaging);
    setRadio("level", state.level);

    if (state.container) onChangeContainer(state.container, false);
    if (state.signature_format)
      onChangeSignatureFormat(state.signature_format, false);

    if (state.fileURL) {
      showPreview(state);
    }
  }

  function setRadio(groupName, value) {
    document.querySelectorAll(`input[name="${groupName}"]`).forEach((r) => {
      r.checked = r.value === value;
    });
  }

  function onChangeContainer(value, resetChildren = true) {
    if (resetChildren) {
      deselectSignatureFormat();
      deselectPackaging();
    }
    saveOption("container", value);

    const isASiC = value === "ASiC-S" || value === "ASiC-E";
    document.getElementById("PAdES").disabled = isASiC;
    document.getElementById("JAdES").disabled = isASiC;
    document.getElementById("XAdES").disabled = false;
    document.getElementById("CAdES").disabled = false;
  }

  function deselectPackaging() {
    ["enveloped", "enveloping", "detached", "internally"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && !el.disabled) el.checked = false;
    });
  }

  function deselectSignatureFormat() {
    ["XAdES", "CAdES", "PAdES", "JAdES"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && !el.disabled) el.checked = false;
    });
  }

  function onChangeSignatureFormat(value, resetChildren = true) {
    if (resetChildren) {
      deselectPackaging();
    }
    saveOption("signature_format", value);

    const form = document.getElementById("options-form");
    const container =
      form.querySelector("input[name='container']:checked")?.value || "No";
    const isASiC = container === "ASiC-S" || container === "ASiC-E";

    if (value === "X") {
      isASiC
        ? setPackagingState(false, false, true, false)
        : setPackagingState(true, true, true, true);
    } else if (value === "C") {
      isASiC
        ? setPackagingState(false, false, true, false)
        : setPackagingState(false, true, true, false);
    } else if (value === "P") {
      setPackagingState(true, false, false, false);
    } else if (value === "J") {
      setPackagingState(false, true, true, false);
    }
  }

  function setPackagingState(enveloped, enveloping, detached, internally) {
    document.getElementById("enveloped").disabled = !enveloped;
    document.getElementById("enveloping").disabled = !enveloping;
    document.getElementById("detached").disabled = !detached;
    document.getElementById("internally").disabled = !internally;
  }

  function showPreview(state) {
    let type = state.fileType;
    let fileURL = state.fileURL;

    const previewArea = document.getElementById("previewArea");
    previewArea.innerHTML = "";

    if (type === "application/pdf") {
      const embed = document.createElement("embed");
      embed.style =
        "height: 500px; width:100%; border: 1px solid #ccc; margin-top: 10px";
      embed.src = fileURL;
      embed.type = "application/pdf";
      previewArea.appendChild(embed);
    } else {
      const isJSON = type === "application/json";
      const isXML = type === "application/xml";
      fetch(fileURL)
        .then((r) => (isJSON ? r.json() : r.text()))
        .then((data) => {
          previewArea.textContent = isJSON
            ? JSON.stringify(data, null, 4)
            : isXML
              ? new XMLSerializer().serializeToString(
                  new DOMParser().parseFromString(data, type),
                )
              : data;
        });
    }
  }

  function confirmDocumentOptions() {
    updateDocumentsList();
    if (!selectedDocument) return;
    const state = documentStates.get(selectedDocument);
    if (!state.container) {
      showToast("Please select a Container before confirming.", "error");
      return;
    }
    if (!state.signature_format) {
      showToast("Please select a Signature Format before confirming.", "error");
      return;
    }
    if (!state.packaging) {
      showToast("Please select a Packaging before confirming.", "error");
      return;
    }
    if (!state.level) {
      showToast("Please select a Level before confirming.", "error");
      return;
    }
    saveOption("confirmed", true);
    lockOptionsPanel(true);
    markDocumentConfirmed(selectedDocument, true);
    showToast(`Options confirmed for ${selectedDocument}`, "success");
    document.getElementById("submit-btn-container").hidden =
      !checkAllConfirmed();
  }

  function lockOptionsPanel(lock) {
    const form = document.getElementById("signature-options");
    form.querySelectorAll("input[type='radio']").forEach((r) => {
      r.disabled = lock;
    });
    document.getElementById("confirm-btn").textContent = lock
      ? "Saved"
      : "Save Options";
    document.getElementById("confirm-btn").disabled = lock;
  }

  function markDocumentConfirmed(filename, confirmed) {
    const el = document.querySelector(`[data-name="${CSS.escape(filename)}"]`);
    if (!el) return;

    const badge = el.querySelector(".status-badge");
    if (confirmed) {
      badge.className = "status-badge success";
      badge.textContent = "Options selected";
    } else if (!confirmed) {
      badge.className = "status-badge pending";
      badge.textContent = "Options needed";
    }
  }

  function checkAllConfirmed() {
    if (documentStates.size === 0) return;
    const allConfirmed = [...documentStates.values()].every((s) => s.confirmed);
    return allConfirmed;
  }

  async function submitAll() {
    if (!checkAllConfirmed()) {
      showToast("The options of all documents were not confirmed.", "error");
      return;
    }

    const formData = new FormData();

    for (const [filename, state] of documentStates.entries()) {
      formData.append(
        "options",
        JSON.stringify({
          filename: filename,
          container: state.container,
          signature_format: state.signature_format,
          packaging: state.packaging,
          level: state.level,
        }),
      );
    }

    formData.append("digest_algorithm", digest_algorithm);

    try {
      const response = await fetch("/rp/document/select", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      // Redirect on success
      window.location.href = "/rp/document/sign";
    } catch (err) {
      console.error("Submit error:", err);
      showToast("Error submitting documents. Please try again.", "error");
    }
  }

  async function handleSubmit() {
    const btn = document.getElementById("submit-btn");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Submitting...`;

    await submitAll();

    btn.disabled = false;
    btn.innerHTML = "Sign document";
  }

  function showToast(message, type = "info") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
      toast.className = "toast";
    }, 3000);
  }