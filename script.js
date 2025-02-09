function flipCoin() {
    let coin = document.getElementById("coin");
    let resultText = document.getElementById("result");

    let outcome = Math.random() < 0.5 ? "Heads" : "Tails";
    
    coin.style.transform = "rotateY(720deg)";
    
    setTimeout(() => {
        resultText.innerText = `Result: ${outcome}`;
        coin.style.transform = "rotateY(0deg)";
    }, 1000);
}
