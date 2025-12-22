# anime.js template
ANIME_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Skeleton Animation (Anime.js)</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/animejs/3.2.1/anime.min.js"></script>
    <style>
        body { background-color: #1e1e1e; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #ccc; font-family: sans-serif; }
        #animation-container { position: relative; width: {{WIDTH}}px; height: {{HEIGHT}}px; overflow: visible; border: 1px solid #333; margin-bottom: 20px; }
        .bone-img { position: absolute; transform-origin: 0 0; }
        .controls { display: flex; gap: 10px; align-items: center; }
        button { background: #444; color: white; border: none; padding: 8px 16px; cursor: pointer; border-radius: 4px; }
        button:hover { background: #555; }
        
        /* Debug Styles */
        body.debug .bone-img { border: 2px solid rgba(255, 0, 0, 0.7); box-sizing: border-box; } /* Red border for Container */
        body.debug .bone-img > div[id$="_img"] { border: 2px solid rgba(0, 255, 0, 0.7); box-sizing: border-box; } /* Green border for Visual */
        /* Draw pivot point */
        .bone-pivot {
            position: absolute; width: 10px; height: 10px; background: cyan; border-radius: 50%; z-index: 1000; pointer-events: none; transform: translate(-50%, -50%); display: none;
        }
        body.debug .bone-pivot { display: block; }
        .pivot-label {
            position: absolute; color: white; font-size: 10px; white-space: nowrap; transform: translate(10px, -50%); display: none;
        }
        body.debug .pivot-label { display: block; }
    </style>
</head>
<body>

<div id="animation-container">
    <!-- Bones will be generated here -->
    {{HTML_STRUCTURE}}
</div>

<div class="controls">
    <button onclick="anim.play()">Play</button>
    <button onclick="anim.pause()">Pause</button>
    <button onclick="anim.restart()">Restart</button>
    <label style="margin-left: 10px"><input type="checkbox" onchange="document.body.classList.toggle('debug', this.checked)"> Debug Bones</label>
</div>

<script>
    // Animation Data
    const animationData = {{ANIMATION_DATA}};
    var anim; // Global timeline instance
    
    // Initialize
    window.onload = function() {
        anim = anime.timeline({
            loop: true,
            autoplay: true,
            duration: {{DURATION_MS}},
            easing: 'linear'
        });

        // Apply animations per bone
        for (const boneName in animationData) {
            const boneEl = document.getElementById(boneName);
            if (!boneEl) continue;

            const props = animationData[boneName];
            
            // Construct config by merging properties
            let config = {
                targets: boneEl,
                duration: {{DURATION_MS}},
                easing: 'linear'
            };
            
            Object.assign(config, props);
            
            anim.add(config, 0); // Offset 0 to start all together
        }
    };
</script>

</body>
</html>
"""