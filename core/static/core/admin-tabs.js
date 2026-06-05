(function () {
    const languageLabels = {
        ru: "RU",
        en: "EN",
        lt: "LT",
    };

    function getPanelLanguage(panel) {
        const select = panel.querySelector('select[name$="-language"]');

        if (!select || !select.value) {
            return "new";
        }

        return select.value;
    }

    function getPanelLabel(panel, index) {
        const language = getPanelLanguage(panel);

        if (languageLabels[language]) {
            return languageLabels[language];
        }

        return `New ${index + 1}`;
    }

    function getPanelTitle(panel) {
        const titleInput = panel.querySelector('input[name$="-title"]');

        if (titleInput && titleInput.value.trim()) {
            return titleInput.value.trim();
        }

        return "Untitled translation";
    }

    function activateTab(group, panelId) {
        group.querySelectorAll(".translation-tab").forEach((tab) => {
            const isActive = tab.dataset.target === panelId;
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", isActive ? "true" : "false");
        });

        group.querySelectorAll(".inline-related").forEach((panel) => {
            panel.classList.toggle("is-active-translation", panel.id === panelId);
        });
    }

    function buildTabs(group) {
        if (!group || group.dataset.tabsReady === "true") {
            return;
        }

        const root = group.querySelector(":scope > fieldset.module") || group;
        const panels = Array.from(root.querySelectorAll(".inline-related")).filter(
            (panel) => !panel.classList.contains("empty-form")
        );

        if (panels.length < 2) {
            return;
        }

        const existingTabs = group.querySelector(".translation-tabs");

        if (existingTabs) {
            existingTabs.remove();
        }

        const tabs = document.createElement("div");
        tabs.className = "translation-tabs";
        tabs.setAttribute("role", "tablist");
        tabs.setAttribute("aria-label", "Article translations");

        panels.forEach((panel, index) => {
            if (!panel.id) {
                panel.id = `translation-panel-${index}`;
            }

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

        if (!heading) {
            return;
        }

        heading.insertAdjacentElement("afterend", tabs);
        group.dataset.tabsReady = "true";
        activateTab(group, panels[0].id);

        group.addEventListener("change", (event) => {
            if (event.target.matches('select[name$="-language"], input[name$="-title"]')) {
                group.dataset.tabsReady = "false";
                buildTabs(group);
            }
        });
    }

    function initTranslationTabs() {
        buildTabs(document.querySelector("#translations-group"));
    }

    window.addEventListener("load", initTranslationTabs);
    document.addEventListener("formset:added", initTranslationTabs);
})();
