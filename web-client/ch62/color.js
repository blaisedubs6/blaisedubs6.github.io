const s = document.createElement('script')
s.nonce = nonce
s.textContent = "alert('test')"
document.body.appendChild(s)
