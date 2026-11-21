# Updraft

A 3D bird flight game in a single HTML file (Three.js, no build step).

Open `index.html` in a browser (it loads Three.js from a CDN, so it needs internet).

## Controls
- **W / S** (or arrows): nose up / nose down
- **A / D**: bank and turn (auto-levels when released)
- **Space**: flap (uses wing strength, refills while gliding)
- **Shift**: tuck wings to dive fast
- Mouse drag: look around · wheel: zoom · **I** invert pitch · **R** reset · **M** sound
- Touch: joystick + FLAP / TUCK buttons. Gamepads work too.

## Physics
Lift and drag from angle of attack (with stall), induced drag, wing area that shrinks when tucked,
flapping thrust, wind with gusts, thermals and ridge lift. Gentle touchdowns land you on ground,
treetops, roofs or the sea; hard impacts make you tumble.
