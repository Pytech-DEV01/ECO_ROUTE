function postJson(url, payload){
  return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(r=>r.json())
}
const loginForm=document.getElementById('loginForm');
if(loginForm){
  loginForm.addEventListener('submit',async e=>{
    e.preventDefault();
    const email=document.getElementById('loginEmail').value.trim();
    const password=document.getElementById('loginPassword').value.trim();
    const res=await postJson('/api/login',{email,password});
    if(res.status==='ok'){window.location.href='/dashboard'} else alert('Login failed')
  })
}
const signupForm=document.getElementById('signupForm');
if(signupForm){
  signupForm.addEventListener('submit',async e=>{
    e.preventDefault();
    const name=document.getElementById('signupName').value.trim();
    const email=document.getElementById('signupEmail').value.trim();
    const password=document.getElementById('signupPassword').value.trim();
    const res=await postJson('/api/signup',{name,email,password});
    if(res.status==='ok'){window.location.href='/login'} else alert('Sign up failed')
  })
}

