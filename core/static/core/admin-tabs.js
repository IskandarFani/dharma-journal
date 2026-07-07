(function () {
    const languageLabels = {
        ru: "RU",
        en: "EN",
        lt: "LT",
    };

    const languageOrder = ["ru", "en", "lt"];
    const storageKey = `article-translation-tab:${window.location.pathname}`;
    let knownPanelCount = 0;
    let pendingAddedCheck = null;

    function getGroup() {
        return document.querySelector("#translations-group");
    }

    function getRoot(group) {
        return group.querySelector(":scope > fieldset.module") || group;
    }

    function getPanels(group) {
        return Array.from(getRoot(group).querySelectorAll(".inline-related")).filter(
            (panel) => !panel.classList.contains("empty-form")
        );
    }

    function getPanelLanguage(panel) {
        const select = panel.querySelector('select[name$="-language"]');
        return select && select.value ? select.value : "";
    }

    function getPanelLabel(panel, index) {
        const language = getPanelLanguage(panel);
        return languageLabels[language] || `New ${index + 1}`;
    }

    function getPanelTitle(panel) {
        const titleInput = panel.querySelector('input[name$="-title"]');

        if (titleInput && titleInput.value.trim()) {
            return titleInput.value.trim();
        }

        return "Untitled translation";
    }

    function getPanelKey(panel) {
        const language = getPanelLanguage(panel);
        const idInput = panel.querySelector('input[name$="-id"]');

        if (language) {
            return `language:${language}`;
        }

        if (idInput && idInput.value) {
            return `id:${idInput.value}`;
        }

        return panel.id || "";
    }

    function ensurePanelIds(panels) {
        panels.forEach((panel, index) => {
            if (!panel.id) {
                panel.id = `translation-panel-${index}`;
            }
        });
    }

    function getActivePanel(group) {
        return group.querySelector(".inline-related.is-active-translation");
    }

    function activateTab(group, panelId) {
        const panels = getPanels(group);
        const activePanel = panels.find((panel) => panel.id === panelId) || panels[0];

        if (!activePanel) {
            return;
        }

        group.querySelectorAll(".translation-tab").forEach((tab) => {
            const isActive = tab.dataset.target === activePanel.id;
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", isActive ? "true" : "false");
            tab.tabIndex = isActive ? 0 : -1;
        });

        panels.forEach((panel) => {
            panel.classList.toggle("is-active-translation", panel.id === activePanel.id);
        });

        sessionStorage.setItem(storageKey, getPanelKey(activePanel));
    }

    function choosePanelToActivate(group, preferredPanel) {
        const panels = getPanels(group);

        if (preferredPanel && panels.includes(preferredPanel)) {
            return preferredPanel;
        }

        const activePanel = getActivePanel(group);

        if (activePanel && panels.includes(activePanel)) {
            return activePanel;
        }

        const storedKey = sessionStorage.getItem(storageKey);

        if (storedKey) {
            const storedPanel = panels.find((panel) => getPanelKey(panel) === storedKey);

            if (storedPanel) {
                return storedPanel;
            }
        }

        return panels[0];
    }

    function assignMissingLanguage(group, panel) {
        const select = panel.querySelector('select[name$="-language"]');

        if (!select || select.value) {
            return;
        }

        const usedLanguages = new Set(
            getPanels(group)
                .filter((candidate) => candidate !== panel)
                .map(getPanelLanguage)
                .filter(Boolean)
        );
        const missingLanguage = languageOrder.find((language) => !usedLanguages.has(language));

        if (missingLanguage) {
            select.value = missingLanguage;
            select.dispatchEvent(new Event("change", { bubbles: true }));
        }
    }

    function updateTotalForms(group) {
        const totalForms = group.querySelector('input[name$="-TOTAL_FORMS"]');

        if (!totalForms) {
            return;
        }

        const panels = getPanels(group);
        const visibleCount = panels.length;
        const maxForms = Number(group.querySelector('input[name$="-MAX_NUM_FORMS"]')?.value || 0);
        const addRow = group.querySelector(".add-row");
        let completeNote = group.querySelector(".translation-complete-note");

        if (maxForms && visibleCount >= maxForms) {
            group.classList.add("translations-complete");

            if (addRow && !completeNote) {
                completeNote = document.createElement("div");
                completeNote.className = "translation-complete-note";
                completeNote.textContent = "All 3 language versions are added.";
                addRow.insertAdjacentElement("afterend", completeNote);
            }
        } else {
            group.classList.remove("translations-complete");

            if (completeNote) {
                completeNote.remove();
            }
        }
    }

    function showPanel(group, panel) {
        if (!group || !panel) {
            return;
        }

        assignMissingLanguage(group, panel);
        buildTabs(group, { preferredPanel: panel });
        panel.scrollIntoView({ block: "start", behavior: "smooth" });
        focusNewPanel(panel);
    }

    function detectAddedPanel(group) {
        if (!group) {
            return;
        }

        const panels = getPanels(group);

        if (panels.length > knownPanelCount) {
            showPanel(group, panels[panels.length - 1]);
            return;
        }

        buildTabs(group);
    }

    function scheduleAddedPanelCheck() {
        window.clearTimeout(pendingAddedCheck);

        pendingAddedCheck = window.setTimeout(() => {
            detectAddedPanel(getGroup());
        }, 80);
    }

    function buildTabs(group, options) {
        if (!group) {
            return;
        }

        const root = getRoot(group);
        const panels = getPanels(group);
        const preferredPanel = options && options.preferredPanel;
        const previousTabs = group.querySelector(".translation-tabs");

        if (previousTabs) {
            previousTabs.remove();
        }

        if (panels.length === 0) {
            group.dataset.tabsReady = "false";
            return;
        }

        ensurePanelIds(panels);

        const tabs = document.createElement("div");
        tabs.className = "translation-tabs";
        tabs.setAttribute("role", "tablist");
        tabs.setAttribute("aria-label", "Article translations");

        panels.forEach((panel, index) => {
            const tab = document.createElement("button");
            tab.type = "button";
            tab.className = "translation-tab";
            tab.dataset.target = panel.id;
            tab.setAttribute("role", "tab");
            tab.setAttribute("aria-controls", panel.id);
            tab.innerHTML = `<strong>${getPanelLabel(panel, index)}</strong><span>${getPanelTitle(panel)}</span>`;
            tab.addEventListener("click", () => activateTab(group, panel.id));
            tabs.appendChild(tab);
        });

        const heading = root.querySelector(":scope > h2");

        if (heading) {
            heading.insertAdjacentElement("afterend", tabs);
        } else {
            root.insertAdjacentElement("afterbegin", tabs);
        }

        group.dataset.tabsReady = "true";
        updateTotalForms(group);
        knownPanelCount = panels.length;
        activateTab(group, choosePanelToActivate(group, preferredPanel).id);
    }

    function refreshTabs(event) {
        const group = getGroup();

        if (!group) {
            return;
        }

        if (
            event.target.matches(
                'select[name$="-language"], input[name$="-title"], input[name$="-DELETE"]'
            )
        ) {
            buildTabs(group);
        }
    }

    function focusNewPanel(panel) {
        const firstEditable = panel.querySelector(
            'select[name$="-language"], input[name$="-title"], textarea, input:not([type="hidden"])'
        );

        if (firstEditable) {
            firstEditable.focus();
        }
    }

    function initTranslationTabs() {
        buildTabs(getGroup());
    }

    window.addEventListener("load", initTranslationTabs);
    document.addEventListener("click", (event) => {
        if (event.target.closest("#translations-group .add-row a")) {
            scheduleAddedPanelCheck();
        }
    });
    document.addEventListener("change", refreshTabs);
    document.addEventListener("input", (event) => {
        if (event.target.matches('input[name$="-title"]')) {
            buildTabs(getGroup());
        }
    });
    document.addEventListener("formset:added", (event) => {
        const group = getGroup();

        if (!group) {
            scheduleAddedPanelCheck();
            return;
        }

        const target = event.target;
        const panel =
            target.closest && target.closest(".inline-related")
                ? target.closest(".inline-related")
                : getPanels(group).at(-1);

        if (!panel || !group.contains(panel)) {
            scheduleAddedPanelCheck();
            return;
        }

        showPanel(group, panel);
    });

    const observer = new MutationObserver((mutations) => {
        const group = getGroup();

        if (!group) {
            return;
        }

        const addedInline = mutations.some((mutation) =>
            Array.from(mutation.addedNodes).some(
                (node) =>
                    node.nodeType === Node.ELEMENT_NODE &&
                    (node.matches?.(".inline-related") || node.querySelector?.(".inline-related"))
            )
        );

        if (addedInline) {
            scheduleAddedPanelCheck();
        }
    });

    window.addEventListener("load", () => {
        const group = getGroup();

        if (group) {
            observer.observe(group, { childList: true, subtree: true });
        }
    });
})();
