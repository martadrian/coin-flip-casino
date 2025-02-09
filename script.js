function flipCoin(choice) {
    let coin = document.querySelector("#coin img");
    let resultText = document.getElementById("result");

    let randomFlip = Math.random() < 0.5 ? "heads" : "tails"; // Random result

    // Reset animation first (this ensures re-flipping works)
    coin.style.animation = "none";
    void coin.offsetWidth; // Trigger reflow
    coin.style.animation = randomFlip === "heads" ? "flipHeads 1s ease-in-out" : "flipTails 1s ease-in-out";

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
