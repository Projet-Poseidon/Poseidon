document.addEventListener('DOMContentLoaded', () => {
    const crossContainer = document.getElementById('crossContainer');
    const messageElement = document.getElementById('message');
    const shapeSelector = document.getElementById('shapeSelector');
    const colorSelector = document.getElementById('colorSelector');
    const saveDataButton = document.getElementById('saveDataButton');
    const dataOutput = document.getElementById('dataOutput');
    const textInput = document.getElementById('textInput');
    const dataOutputLabel = document.getElementById('dataOutputLabel');
    const textInputENI = document.getElementById('textInputENI');
    // NOUVEAU: Récupérer le troisième encart de texte
    const textInputDefense = document.getElementById('textInputDefense');

    let currentMode = shapeSelector.value;
    let shapeCount = 0;
    let firstClickPoint = null;

    let originalImageWidth;
    let originalImageHeight;

    let isResizing = false;
    let isDragging = false;
    let isRotating = false;
    let activeElement = null;
    let initialX, initialY, initialWidth, initialHeight, initialLeft, initialTop;
    let resizeHandleClass = '';
    let ignoreNextClick = false;

    let initialAngle = 0;
    let initialCenter = {};
    let currentAngle = 0;

    const history = [];
    const MAX_HISTORY_SIZE = 20;

    // --- Fonctions utilitaires pour l'historique ---
    function saveState() {
        const containerHTML = crossContainer.innerHTML;
        if (history.length >= MAX_HISTORY_SIZE) {
            history.shift();
        }
        history.push(containerHTML);
    }

    function undo() {
        if (history.length > 1) {
            history.pop();
            const lastState = history[history.length - 1];
            crossContainer.innerHTML = lastState;
            attachEventListenersToElements();
            messageElement.textContent = 'Action annulée.';
        } else {
            messageElement.textContent = 'Historique vide. Rien à annuler.';
        }
    }
    saveState();

    // --- Définition et chargement des images et des options ---
    const images = {
        'semparer': { img: new Image(), option: shapeSelector.querySelector('option[value="semparer"]') },
        'neutraliser': { img: new Image(), option: shapeSelector.querySelector('option[value="neutraliser"]') },
        'fixer': { img: new Image(), option: shapeSelector.querySelector('option[value="fixer"]') },
        'detruire': { img: new Image(), option: shapeSelector.querySelector('option[value="detruire"]') }
    };
    
    images.semparer.img.src = 'Forme/semparer_de.png';
    images.neutraliser.img.src = 'Forme/neutraliser.png';
    images.fixer.img.src = 'Forme/fixer.png';
    images.detruire.img.src = 'Forme/detruire.png';

    const imageFond = new Image();
    imageFond.src = 'mon_fond.png';

    function loadImageAndEnableOption(imageObject) {
        imageObject.option.disabled = true;
        imageObject.img.onload = () => {
            console.log(`L'image '${imageObject.img.src}' a été chargée avec succès.`);
            imageObject.option.disabled = false;
        };
        imageObject.img.onerror = () => {
            console.error(`Erreur de chargement pour '${imageObject.img.src}'. Vérifiez le chemin.`);
        };
    }
    
    Object.values(images).forEach(loadImageAndEnableOption);

    imageFond.onload = () => {
        originalImageWidth = imageFond.naturalWidth;
        originalImageHeight = imageFond.naturalHeight;
    };

    shapeSelector.addEventListener('change', (event) => {
        currentMode = event.target.value;
        firstClickPoint = null;
        messageElement.textContent = '';
        if (currentMode === 'arrow') {
            messageElement.textContent = 'Cliquez pour le point de départ de la flèche.';
        }
    });

    // --- Fonctions de gestion des événements ---
    function selectElement(element) {
        document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        if (element) {
            element.classList.add('selected');
        }
    }

    function attachEventListenersToElements() {
        document.querySelectorAll('.placed-image-container, .shape, .arrow-container').forEach(el => {
            el.removeEventListener('mousedown', elementMousedownHandler);
        });

        document.querySelectorAll('.placed-image-container, .shape, .arrow-container').forEach(el => {
            el.addEventListener('mousedown', elementMousedownHandler);
        });
    }

    function elementMousedownHandler(event) {
        selectElement(event.currentTarget);
        activeElement = event.currentTarget;
        if (event.currentTarget.classList.contains('placed-image-container') || event.currentTarget.classList.contains('arrow-container')) {
            isDragging = true;
            initialX = event.clientX;
            initialY = event.clientY;
            initialLeft = activeElement.offsetLeft;
            initialTop = activeElement.offsetTop;
            activeElement.style.zIndex = '1000';
            event.preventDefault();
        }
    }
    attachEventListenersToElements();
    
    // --- Fonctions de placement et de manipulation ---
    function applyColor(element, color) {
        if (color === 'red') {
            element.classList.add('red');
            element.classList.remove('blue');
        } else if (color === 'blue') {
            element.classList.add('blue');
            element.classList.remove('red');
        } else {
            element.classList.remove('red', 'blue');
        }
    }

    function placeImage(x, y, imageObject) {
        if (!imageObject.img.complete) {
            messageElement.textContent = 'L\'image n\'est pas encore chargée. Veuillez réessayer.';
            return;
        }

        const selectedColor = colorSelector.value;
        
        const imageContainer = document.createElement('div');
        imageContainer.classList.add('placed-image-container');
        applyColor(imageContainer, selectedColor);

        imageContainer.style.left = `${x}px`;
        imageContainer.style.top = `${y}px`;
        imageContainer.style.transform = `translate(-50%, -50%) rotate(0deg)`;
        imageContainer.style.width = `${imageObject.img.naturalWidth / 2}px`;
        imageContainer.style.height = `${imageObject.img.naturalHeight / 2}px`;

        // AJOUT: Stockage des données de l'objet
        imageContainer.dataset.type = currentMode;
        imageContainer.dataset.color = selectedColor;
        imageContainer.dataset.x = x;
        imageContainer.dataset.y = y;

        const imageElement = document.createElement('img');
        imageElement.src = imageObject.img.src;
        imageContainer.appendChild(imageElement);

        imageContainer.innerHTML += `
            <div class="resize-handle top-left"></div>
            <div class="resize-handle top-right"></div>
            <div class="resize-handle bottom-left"></div>
            <div class="resize-handle bottom-right"></div>
            <div class="rotate-handle"></div>
        `;

        crossContainer.appendChild(imageContainer);
        selectElement(imageContainer);
        shapeCount++;
        messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou image(s).`;
        saveState();
    }

    function drawArrow(p1, p2) {
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const length = Math.sqrt(dx * dx + dy * dy);
        const angleRad = Math.atan2(dy, dx);
        const arrowContainer = document.createElement('div');
        arrowContainer.classList.add('arrow-container');
        arrowContainer.style.left = `${p1.x}px`;
        arrowContainer.style.top = `${p1.y}px`;
        arrowContainer.style.transform = `rotate(${angleRad * 180 / Math.PI}deg)`;

        const line = document.createElement('div');
        line.classList.add('arrow-line');
        line.style.width = `${length}px`;

        const arrowhead = document.createElement('div');
        arrowhead.classList.add('arrowhead');
        arrowhead.textContent = '▶';
        arrowhead.style.left = `${length}px`;
        
        const selectedColor = colorSelector.value;
        if (selectedColor === 'red') {
             line.style.backgroundColor = '#ff0000';
             arrowhead.style.color = '#ff0000';
        } else if (selectedColor === 'blue') {
             line.style.backgroundColor = '#0000ff';
             arrowhead.style.color = '#0000ff';
        } else {
             line.style.backgroundColor = '#0000ff';
             arrowhead.style.color = '#0000ff';
        }

        // AJOUT: Stockage des données de l'objet flèche
        arrowContainer.dataset.type = currentMode;
        arrowContainer.dataset.color = selectedColor;
        arrowContainer.dataset.startx = p1.x;
        arrowContainer.dataset.starty = p1.y;
        arrowContainer.dataset.endx = p2.x;
        arrowContainer.dataset.endy = p2.y;

        arrowContainer.appendChild(line);
        arrowContainer.appendChild(arrowhead);
        crossContainer.appendChild(arrowContainer);
        selectElement(arrowContainer);
    }

    function placeShape(x, y, mode) {
        const shapeElement = document.createElement('div');
        shapeElement.classList.add('shape');

        const selectedColor = colorSelector.value;
        if (selectedColor === 'red') {
            shapeElement.style.color = '#ff0000';
        } else if (selectedColor === 'blue') {
            shapeElement.style.color = '#0000ff';
        }

        if (mode === 'cross') {
            shapeElement.textContent = '✖';
            shapeElement.classList.add('cross');
        } else if (mode === 'circle') {
            shapeElement.textContent = '●';
            shapeElement.classList.add('circle');
        }

        shapeElement.style.left = `${x}px`;
        shapeElement.style.top = `${y}px`;
        shapeElement.style.transform = `translate(-50%, -50%) rotate(0deg)`;

        // AJOUT: Stockage des données de l'objet forme
        shapeElement.dataset.type = mode;
        shapeElement.dataset.color = selectedColor;
        shapeElement.dataset.x = x;
        shapeElement.dataset.y = y;

        crossContainer.appendChild(shapeElement);
        selectElement(shapeElement);
        shapeCount++;
        messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou flèche(s).`;
        saveState();
    }
    
    // --- Fonctions de calcul et d'événement ---
    crossContainer.addEventListener('mousedown', (event) => {
        const target = event.target;
        if (target.classList.contains('resize-handle')) {
            isResizing = true;
            activeElement = target.parentElement;
            initialX = event.clientX;
            initialY = event.clientY;
            initialWidth = activeElement.offsetWidth;
            initialHeight = activeElement.offsetHeight;
            initialLeft = activeElement.offsetLeft;
            initialTop = activeElement.offsetTop;
            resizeHandleClass = target.classList[1];
            event.preventDefault();
            ignoreNextClick = true;
        } 
        else if (target.classList.contains('rotate-handle')) {
            isRotating = true;
            activeElement = target.parentElement;
            initialX = event.clientX;
            initialY = event.clientY;
            const rect = activeElement.getBoundingClientRect();
            initialCenter = {
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2
            };
            initialAngle = getRotation(activeElement);
            event.preventDefault();
            ignoreNextClick = true;
        }
        else if (target.closest('.placed-image-container') || target.closest('.shape') || target.closest('.arrow-container')) {
            return;
        } else {
            selectElement(null);
            activeElement = null;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing || isDragging || isRotating) {
            saveState();
            ignoreNextClick = true;
        }
        if (activeElement) {
            activeElement.style.zIndex = '';
        }
        isResizing = false;
        isDragging = false;
        isRotating = false;
        
        setTimeout(() => {
            ignoreNextClick = false;
        }, 0);
    });

    document.addEventListener('mousemove', (event) => {
        if (isResizing || isDragging || isRotating) {
            ignoreNextClick = true;
        }
        
        if (isResizing) {
            const dx = event.clientX - initialX;
            const dy = event.clientY - initialY;
            let newWidth = initialWidth;
            let newHeight = initialHeight;
            let newLeft = initialLeft;
            let newTop = initialTop;

            if (resizeHandleClass.includes('left')) {
                newWidth = initialWidth - dx;
                newLeft = initialLeft + dx;
            } else if (resizeHandleClass.includes('right')) {
                newWidth = initialWidth + dx;
            }
            if (resizeHandleClass.includes('top')) {
                newHeight = initialHeight - dy;
                newTop = initialTop + dy;
            } else if (resizeHandleClass.includes('bottom')) {
                newHeight = initialHeight + dy;
            }

            activeElement.style.width = `${Math.max(20, newWidth)}px`;
            activeElement.style.height = `${Math.max(20, newHeight)}px`;
            activeElement.style.left = `${newLeft}px`;
            activeElement.style.top = `${newTop}px`;
        } 
        else if (isRotating) {
            const angleRad = Math.atan2(event.clientY - initialCenter.y, event.clientX - initialCenter.x);
            const initialAngleRad = Math.atan2(initialY - initialCenter.y, initialX - initialCenter.x);
            const deltaAngle = (angleRad - initialAngleRad) * (180 / Math.PI);
            currentAngle = initialAngle + deltaAngle;
            
            const currentTransform = activeElement.style.transform;
            let transformParts = currentTransform.split(/\s(?=[\w])/).filter(p => !p.startsWith('rotate'));
            transformParts.push(`rotate(${currentAngle}deg)`);
            activeElement.style.transform = transformParts.join(' ');
        }
        else if (isDragging) {
            const dx = event.clientX - initialX;
            const dy = event.clientY - initialY;
            activeElement.style.left = `${initialLeft + dx}px`;
            activeElement.style.top = `${initialTop + dy}px`;
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.key === 'z') {
            event.preventDefault();
            undo();
            return;
        }
        const selectedElement = document.querySelector('.selected');
        if (event.key === 'Delete' || event.key === 'Backspace') {
            if (selectedElement) {
                selectedElement.remove();
                messageElement.textContent = 'Élément supprimé.';
                saveState();
            }
        }
    });

    crossContainer.addEventListener('click', (event) => {
        if (ignoreNextClick) {
            ignoreNextClick = false;
            return;
        }
        
        if (event.target.closest('.placed-image-container, .shape, .arrow-container')) {
            const clickedElement = event.target.closest('.placed-image-container, .shape, .arrow-container');
            selectElement(clickedElement);
            return;
        }
        
        const containerRect = crossContainer.getBoundingClientRect();
        const x = event.clientX - containerRect.left;
        const y = event.clientY - containerRect.top;

        const imageDimensions = getBackgroundImageDimensions();
        const imgX = imageDimensions.offsetX;
        const imgY = imageDimensions.offsetY;
        const imgWidth = imageDimensions.width;
        const imgHeight = imageDimensions.height;

        if (x < imgX || x > imgX + imgWidth || y < imgY || y > imgY + imgHeight) {
            messageElement.textContent = 'Veuillez cliquer sur l\'image.';
            return;
        }

        selectElement(null);

        if (images[currentMode]) {
            placeImage(x, y, images[currentMode]);
        } else if (currentMode === 'arrow') {
            if (!firstClickPoint) {
                firstClickPoint = { x: x, y: y };
                messageElement.textContent = 'Cliquez pour le point d\'arrivée de la flèche.';
            } else {
                drawArrow(firstClickPoint, { x: x, y: y });
                firstClickPoint = null;
                shapeCount++;
                messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou flèche(s).`;
                saveState();
            }
        } else {
            placeShape(x, y, currentMode);
        }
        attachEventListenersToElements();
    });
    
    function getRotation(element) {
        const transform = element.style.transform;
        const match = transform.match(/rotate\(([^)]+)deg\)/);
        if (match) {
            return parseFloat(match[1]);
        }
        return 0;
    }

    function getBackgroundImageDimensions() {
        if (!originalImageWidth || !originalImageHeight) {
            return { width: 0, height: 0, offsetX: 0, offsetY: 0 };
        }
        const containerRect = crossContainer.getBoundingClientRect();
        const containerRatio = containerRect.width / containerRect.height;
        const imageRatio = originalImageWidth / originalImageHeight;
        let renderedWidth, renderedHeight;
        if (containerRatio > imageRatio) {
            renderedHeight = containerRect.height;
            renderedWidth = renderedHeight * imageRatio;
        } else {
            renderedWidth = containerRect.width;
            renderedHeight = renderedWidth / imageRatio;
        }
        const offsetX = (containerRect.width - renderedWidth) / 2;
        const offsetY = (containerRect.height - renderedHeight) / 2;
        return {
            width: renderedWidth,
            height: renderedHeight,
            offsetX: offsetX,
            offsetY: offsetY
        };
    }
    
    // NOUVEAU: Gérer l'événement de clic du bouton de sauvegarde
    saveDataButton.addEventListener('click', () => {
        const elements = document.querySelectorAll('.placed-image-container, .shape, .arrow-container');
        const data = [];
        elements.forEach(el => {
            const elType = el.classList.contains('placed-image-container') ? 'image' : (el.classList.contains('arrow-container') ? 'arrow' : 'shape');
            const elementData = {
                type: elType,
                color: el.dataset.color || 'none',
                // NOUVEAU: Récupérer la rotation et la taille
                rotation: getRotation(el),
                width: el.offsetWidth,
                height: el.offsetHeight
            };
            
            // Collecte des coordonnées spécifiques au type d'objet
            if (elType === 'image' || elType === 'shape') {
                elementData.x = el.offsetLeft + el.offsetWidth / 2;
                elementData.y = el.offsetTop + el.offsetHeight / 2;
                elementData.subtype = el.dataset.type; // Ex: 'semparer', 'fixer'
            } else if (elType === 'arrow') {
                elementData.start = { x: el.dataset.startx, y: el.dataset.starty };
                elementData.end = { x: el.dataset.endx, y: el.dataset.endy };
            }
            data.push(elementData);
        });

        // NOUVEAU: Créer un objet final qui inclut les éléments et les notes
        const finalData = {
            notes: textInput.value,
            notesENI: textInputENI.value,
            notesDefense: textInputDefense.value,
            elements: data
        };

        const jsonOutput = JSON.stringify(finalData, null, 2);
        dataOutput.value = jsonOutput;
        dataOutputLabel.style.display = 'block';
        dataOutput.style.display = 'block';
        messageElement.textContent = 'Données sauvegardées en JSON. Copiez-les depuis la zone de texte.';
    });
});
