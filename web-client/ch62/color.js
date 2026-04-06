async function envoyerDonnees() {
  try {
    const response = await fetch("https://recept.free.beeceptor.com/g", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        nom: "Blaise",
        age: 25
      })
    });

    const data = await response.json();
    console.log("Réponse :", data);
  } catch (error) {
    console.log("Erreur :");
  }
}

envoyerDonnees();
  
