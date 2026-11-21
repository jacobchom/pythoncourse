# Updraft

A 3D bird flight game in a single HTML file (Three.js, no build step).

Open `index.html` in a browser (it loads Three.js from a CDN, so it needs internet).

## Controls
- **Mouse aim (default):** move the mouse and the bird flies toward the white circle.
  Hold **left click / Space** to flap, **right click / Shift** to tuck and dive.
- **Keys:** W/S nose up/down, A/D bank and turn (auto-levels), Space flap, Shift tuck. Keys override the mouse.
- **Touch:** stick to steer, FLAP and TUCK buttons. Gamepads work too.
- Esc (or the II button) pauses and opens settings: steering, Easy/Realistic help, time of day, graphics, invert, sound.

## Helping you fly
- A six-step tutorial on first launch (climb, turn, dive, ride rising air, fly through a ring, land).
- Easy mode: no stalls, auto-flap when you ask to climb while slow, auto-flare before touchdown, gentler landings.
- Green marker points to the nearest rising air; variometer beeps when you climb; PULL UP warning; ground shadow under the bird.
- Graphics lower themselves automatically if the frame rate drops.

## Physics
Lift and drag from angle of attack (with stall), induced drag, wing area that shrinks when tucked,
flapping thrust, wind with gusts, thermals and ridge lift. Gentle touchdowns land you on ground,
treetops, roofs or the sea; hard impacts make you tumble.
