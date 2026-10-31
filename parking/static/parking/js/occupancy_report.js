body {
    margin: 0;
    padding: 35px 7 %;
    background: #080b10;
    color: #f3f4f6;
    font - family: Arial, sans - serif;
}

h1 {
    color: #2ecc71;
    letter - spacing: 2px;
}

h2 {
    font - size: 30px;
}

h3 {
    color: #60a5fa;
    margin - top: 32px;
}

h4 {
    padding: 14px;
    background: #121821;
    border - left: 4px solid #2ecc71;
    border - radius: 5px;
    font - size: 19px;
}

body > p {
    color: #b6c0cc;
}

body > p: nth - of - type(n + 2) {
    display: inline - block;
    padding: 16px;
    margin: 7px;
    min - width: 150px;
    background: #121821;
    border: 1px solid #293342;
    border - radius: 10px;
}

a {
    color: #2ecc71;
    text - decoration: none;
}

a:hover {
    text - decoration: underline;
}

hr {
    border: 0;
    border - top: 1px solid #293342;
    margin: 28px 0;
}

@media(max - width: 600px) {
    body {
        padding: 22px 5 %;
    }

    body > p: nth - of - type(n + 2) {
        display: block;
    }
}