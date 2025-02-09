function flipCoin(choice) {
    let coin = document.querySelector("#coin img");
    let resultText = document.getElementById("result");

    let randomFlip = Math.random() < 0.5 ? "heads" : "tails"; // Random result
    let rotateValue = randomFlip === "heads" ? "rotateY(720deg)" : "rotateY(900deg)";

    // Animate the coin
    coin.style.transform = rotateValue;

    setTimeout(() => {
        if (choice === randomFlip) {
            resultText.innerHTML = "You Won! 🎉";
            resultText.style.color = "green";
        } else {
            resultText.innerHTML = "You Lost! ❌";
            resultText.style.color = "red";
        }
    }, 1000);
}
