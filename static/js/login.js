function login() {
    username = document.getElementById("username").value;
    password = document.getElementById('password').value;

    window.location.href = `/login?username=${username}&pass=${password}`
}