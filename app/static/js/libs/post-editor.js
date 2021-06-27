class PostEditor extends HTMLElement {
    constructor() {
        super();
        const shadow = this.attachShadow({mode: 'closed'});

        const linkElem = document.createElement('link');
        linkElem.setAttribute('rel', 'stylesheet');
        linkElem.setAttribute('href', '/static/css/post-editor.css');

        // Attach the created element to the shadow dom
        shadow.appendChild(linkElem);

        const article = document.createElement("article");
        this.sectionsHolder = document.createElement("div");
        this.sectionsHolder.setAttribute("id", "sections-holder");

        let sections = []
        if (this.hasAttribute("sections")) {
            sections = JSON.parse(this.getAttribute("sections").substr("data:json,".length));
        }

        if (sections.length === 0) {
            sections.push({
                content: "",
                type: "text",
                original: "",
                position: 0
            });
        }

        for (const section of sections) {
            const label = document.createElement("label");
            label.setAttribute("id", `section-${section.position}`)
            if (section.position === 0) {
                label.textContent = "Excerpt";
            } else if (section.position === 1) {
                label.textContent = "Content:";
                label.setAttribute("aria-label", `Content of section #${section.position}`)
            } else {
                label.setAttribute("aria-label", `Content of section #${section.position}`)
            }
            this.sectionsHolder.appendChild(this.#createSection(label, section.content, section.type, section.original));
        }
        article.appendChild(this.sectionsHolder);

        const sc = this.sectionsHolder;
        const addSectionButton = document.createElement("button");
        addSectionButton.textContent = "Add section";
        addSectionButton.addEventListener('click', () => {
            const label = document.createElement("label");
            if (sc.children.length === 0) {
                label.textContent = "Excerpt";
            } else if (sc.children.length === 1) {
                label.textContent = "Content:";
                label.setAttribute("aria-label", `Content of section #${sc.children.length}`)
            } else {
                label.setAttribute("aria-label", `Content of section #${sc.children.length}`)
            }
            sc.appendChild(this.#createSection(label, "", "text", ""));
        });
        article.appendChild(addSectionButton);
        shadow.appendChild(article);
    }

    #createSection(label, text, type, original, position) {
        const section = document.createElement("section");
        if (original) {
            section.setAttribute("class", "with-translation")
        }
        const textArea = document.createElement("textarea");
        section.appendChild(label);
        textArea.textContent = text;
        section.appendChild(textArea);

        if (original?.length > 0) {
            const divOriginal = document.createElement("div");
            divOriginal.setAttribute("class", "original");
            divOriginal.innerHTML = original;
            section.appendChild(divOriginal);
        }

        const select = document.createElement("select");
        const textOption = document.createElement("option");
        textOption.setAttribute("value", "text");
        textOption.setAttribute("selected", "");
        textOption.textContent = "Text";
        select.appendChild(textOption);
        section.appendChild(select);

        const deleteButton = document.createElement("button");
        deleteButton.textContent = "Delete section";
        deleteButton.addEventListener('click', (event) => {
            if (window.confirm("Do you really want to delete the section?")) {
              event.target.parentNode.parentNode.removeChild(event.target.parentNode);
            }
        });
        section.appendChild(deleteButton);

        return section;
    }

    getSections() {
        const sections = [];
        const sectionElements = this.sectionsHolder.children;
        for (let i = 0; i < sectionElements.length; i++) {
            sections.push({
                content: sectionElements[i].querySelector("textarea").value,
                type: sectionElements[i].querySelector("select").value,
                position: i
            })
        }
        return sections;
    }
}

customElements.define('post-editor', PostEditor);