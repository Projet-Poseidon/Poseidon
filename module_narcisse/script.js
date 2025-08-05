document.addEventListener('DOMContentLoaded', () => {
    const crossContainer = document.getElementById('crossContainer');
    const messageElement = document.getElementById('message');
    const shapeSelector = document.getElementById('shapeSelector');

    let currentMode = shapeSelector.value;
    let shapeCount = 0;
    let firstClickPoint = null; 

    let originalImageWidth;
    let originalImageHeight;

    // Variables pour la gestion du redimensionnement
    let isResizing = false;
    let activeElement = null;
    let initialX, initialY, initialWidth, initialHeight;

    // Créer une balise image pour récupérer les dimensions de l'image de fond
    const imageFond = new Image();
    imageFond.src = 'mon_fond.png';

    // Créer une balise image pour l'image à placer
    const imageSemparerDe = new Image();
    imageSemparerDe.src = 'Forme/semparer_de.png';

    // Désactiver l'option de l'image tant qu'elle n'est pas chargée
    const optionImage = shapeSelector.querySelector('option[value="image"]');
    optionImage.disabled = true;

    imageSemparerDe.onload = () => {
        console.log("L'image 'semparer_de.png' a été chargée avec succès.");
        // Activer l'option une fois que l'image est prête
        optionImage.disabled = false;
    };
    imageSemparerDe.onerror = () => {
        console.error("Erreur de chargement pour 'semparer_de.png'. Vérifiez le chemin.");
    };

    imageFond.onload = () => {
        originalImageWidth = imageFond.naturalWidth;
        originalImageHeight = imageFond.naturalHeight;
        
        shapeSelector.addEventListener('change', (event) => {
            currentMode = event.target.value;
            firstClickPoint = null;
            messageElement.textContent = '';
            if (currentMode === 'arrow') {
                messageElement.textContent = 'Cliquez pour le point de départ de la flèche.';
            }
        });
    
        crossContainer.addEventListener('mousedown', (event) => {
            if (event.target.classList.contains('resize-handle')) {
                isResizing = true;
                activeElement = event.target.parentElement;
                initialX = event.clientX;
                initialY = event.clientY;
                initialWidth = activeElement.offsetWidth;
                initialHeight = activeElement.offsetHeight;
                event.preventDefault(); // Empêche la sélection de texte
            }
        });

        crossContainer.addEventListener('mouseup', () => {
            isResizing = false;
        });
        
        crossContainer.addEventListener('mousemove', (event) => {
            if (!isResizing) return;
            
            const dx = event.clientX - initialX;
            const dy = event.clientY - initialY;

            // Logique de redimensionnement
            if (event.target.classList.contains('top-left')) {
                activeElement.style.width = `${initialWidth - dx}px`;
                activeElement.style.height = `${initialHeight - dy}px`;
                activeElement.style.left = `${parseFloat(activeElement.style.left) + dx}px`;
                activeElement.style.top = `${parseFloat(activeElement.style.top) + dy}px`;
            } else if (event.target.classList.contains('top-right')) {
                activeElement.style.width = `${initialWidth + dx}px`;
                activeElement.style.height = `${initialHeight - dy}px`;
                activeElement.style.top = `${parseFloat(activeElement.style.top) + dy}px`;
            } else if (event.target.classList.contains('bottom-left')) {
                activeElement.style.width = `${initialWidth - dx}px`;
                activeElement.style.height = `${initialHeight + dy}px`;
                activeElement.style.left = `${parseFloat(activeElement.style.left) + dx}px`;
            } else if (event.target.classList.contains('bottom-right')) {
                activeElement.style.width = `${initialWidth + dx}px`;
                activeElement.style.height = `${initialHeight + dy}px`;
            }
        });

        crossContainer.addEventListener('click', (event) => {
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
    
            if (currentMode === 'arrow') {
                if (!firstClickPoint) {
                    firstClickPoint = { x: x, y: y };
                    messageElement.textContent = 'Cliquez pour le point de départ de la flèche.';
                } else {
                    const secondClickPoint = { x: x, y: y };
                    drawArrow(firstClickPoint, secondClickPoint);
                    firstClickPoint = null;
                    shapeCount++;
                    messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou flèche(s).`;
                }
            } else if (currentMode === 'image') {
                if (imageSemparerDe.complete) {
                    // Création du conteneur et des poignées pour l'image
                    const imageContainer = document.createElement('div');
                    imageContainer.classList.add('placed-image-container');
                    imageContainer.style.left = `${x}px`;
                    imageContainer.style.top = `${y}px`;
                    imageContainer.style.transform = 'translate(-50%, -50%)'; // Centre l'image sur le curseur
                    imageContainer.style.width = `${imageSemparerDe.naturalWidth}px`;
                    imageContainer.style.height = `${imageSemparerDe.naturalHeight}px`;

                    const imageElement = document.createElement('img');
                    imageElement.src = imageSemparerDe.src;

                    imageContainer.appendChild(imageElement);
                    imageContainer.innerHTML += `
                        <div class="resize-handle top-left"></div>
                        <div class="resize-handle top-right"></div>
                        <div class="resize-handle bottom-left"></div>
                        <div class="resize-handle bottom-right"></div>
                    `;

                    crossContainer.appendChild(imageContainer);
                    shapeCount++;
                    messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou image(s).`;
                } else {
                    messageElement.textContent = 'L\'image n\'est pas encore chargée. Veuillez réessayer.';
                }
            } else {
                const shapeElement = document.createElement('div');
                shapeElement.classList.add('shape');
    
                if (currentMode === 'cross') {
                    shapeElement.textContent = '✖';
                    shapeElement.classList.add('cross');
                } else if (currentMode === 'circle') {
                    shapeElement.textContent = '●';
                    shapeElement.classList.add('circle');
                }
    
                shapeElement.style.left = `${x}px`;
                shapeElement.style.top = `${y}px`;
    
                crossContainer.appendChild(shapeElement);
    
                shapeCount++;
                messageElement.textContent = `Vous avez placé ${shapeCount} forme(s) ou flèche(s).`;
            }
        });
    
        function drawArrow(p1, p2) {
            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;
            const length = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx);
    
            const arrowContainer = document.createElement('div');
            arrowContainer.classList.add('arrow-container');
            arrowContainer.style.left = `${p1.x}px`;
            arrowContainer.style.top = `${p1.y}px`;
            arrowContainer.style.transform = `rotate(${angle}rad)`;
    
            const line = document.createElement('div');
            line.classList.add('arrow-line');
            line.style.width = `${length}px`;
    
            const arrowhead = document.createElement('div');
            arrowhead.classList.add('arrowhead');
            arrowhead.textContent = '▶';
            arrowhead.style.left = `${length}px`;
    
            arrowContainer.appendChild(line);
            arrowContainer.appendChild(arrowhead);
            crossContainer.appendChild(arrowContainer);
        }
    };
    
    function getBackgroundImageDimensions() {
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
});