document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("headsBtn").addEventListener("click", function() {
        flipCoin("heads");
    });

    document.getElementById("tailsBtn").addEventListener("click", function() {
        flipCoin("tails");
    });

    function flipCoin(choice) {
        let coin = document.getElementById("coinImage");
        let result = Math.random() < 0.5 ? "heads" : "tails";

        // Add flip animation
        coin.classList.add("flip");

        setTimeout(() => {
            coin.classList.remove("flip");
            document.getElementById("result").innerText = `The coin landed on: ${result}`;

            if (choice === result) {
                alert("🎉 Congratulations! You guessed correctly.");
            } else {
                alert("❌ Oops! Try again.");
            }
        }, 1000);
    }
});
