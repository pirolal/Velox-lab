async function initCountdown() {
    try {
        const response = await fetch('/api/gare');
        const data = await response.json();
        const gare = data.items;

        if (gare && gare.length > 0) {
            const oraAttuale = new Date().getTime();

            // 1. Creiamo i timestamp completi (Data + Orario Partenza)
            const gareConTimestamp = gare.map(g => {
                // Costruiamo la stringa ISO: "YYYY-MM-DDTHH:mm:00"
                // g.orario_partenza nel tuo DB è ad esempio "09:45"
                const orarioPartenza = g.orario_partenza || "00:00";
                const stringaDataOra = `${g.data_gara}T${orarioPartenza}:00`;
                
                return {
                    ...g,
                    timestampTarget: new Date(stringaDataOra).getTime()
                };
            });

            // 2. Troviamo la gara più vicina nel futuro
            const prossimaGara = gareConTimestamp
                .filter(g => g.timestampTarget > oraAttuale)
                .sort((a, b) => a.timestampTarget - b.timestampTarget)[0];

            if (prossimaGara) {
                const countdownBox = document.getElementById('main-countdown');
                const nameDisplay = document.getElementById('next-race-name-header');
                
                if (countdownBox) countdownBox.style.display = 'block';
                if (nameDisplay) {
                    nameDisplay.innerText = "PROSSIMA GARA: " + prossimaGara.nome.toUpperCase();
                }
                
                // 3. Avviamo il timer con il timestamp preciso (es. 09:45)
                startTimer(prossimaGara.timestampTarget);
            }
        }
    } catch (error) {
        console.error("Errore nel caricamento del countdown:", error);
    }
}

function startTimer(targetTimestamp) {
    const update = () => {
        const ora = new Date().getTime();
        const distanza = targetTimestamp - ora;

        if (distanza < 0) {
            document.getElementById('main-countdown').style.display = 'none';
            return;
        }

        const d = Math.floor(distanza / (1000 * 60 * 60 * 24));
        const h = Math.floor((distanza % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const m = Math.floor((distanza % (1000 * 60 * 60)) / (1000 * 60));
        const s = Math.floor((distanza % (1000 * 60)) / 1000);

        // Aggiorniamo i numeri nell'HTML
        document.getElementById('days').innerText = d.toString().padStart(2, '0');
        document.getElementById('hours').innerText = h.toString().padStart(2, '0');
        document.getElementById('minutes').innerText = m.toString().padStart(2, '0');
        document.getElementById('seconds').innerText = s.toString().padStart(2, '0');
    };
    
    update(); // Esegui subito
    setInterval(update, 1000); // Poi ogni secondo
}

document.addEventListener('DOMContentLoaded', initCountdown);