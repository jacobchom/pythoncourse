# Updraft

A 3D peregrine falcon flight-and-hunting game in a single HTML file (Three.js, no build step).

Climb on rising air, pick out prey (red diamond), fold your wings and stoop at 250-300 km/h.
Pigeon flocks scatter and jink, rabbits bolt and zigzag, fish surface and jump near the coast.
Fly through prey to catch it; faster strikes score more.

Open `index.html` in a browser (it loads Three.js from a CDN, so it needs internet).

## Controls
- **Mouse aim (default):** move the mouse and the bird flies toward the white circle.
  Hold **Space** to flap (unlimited; let go to glide), **right click / Shift** to tuck and dive.
- **Keys:** W/S nose up/down, A/D bank and turn (auto-levels), Space flap, Shift tuck. Keys override the mouse.
- **Touch:** stick to steer, FLAP and TUCK buttons. Gamepads work too.
- Esc (or the II button) pauses and opens settings: steering, Easy/Realistic help, time of day, graphics, invert, sound.

## Helping you fly
- A six-step tutorial on first launch (climb, turn, dive, ride rising air, fly through a ring, land).
- Easy mode: no stalls, auto-flare before touchdown, gentler landings.
- Green marker points to the nearest rising air; variometer beeps when you climb; PULL UP warning; ground shadow under the bird.
- Graphics lower themselves automatically if the frame rate drops.

## Physics
Peregrine-like numbers: 0.9 kg, about 1.1 m span, cruises around 55 km/h, tucked stoop terminal speed near 300 km/h,
pull-outs limited to about 10 g. Easy mode adds strike homing in the last 70 m and a bigger catch radius.

Lift and drag from angle of attack (with stall), induced drag, wing area that shrinks when tucked,
flapping thrust (only while Space is held, no stamina limit), wind with gusts, thermals and ridge lift. Gentle touchdowns land you on ground,
treetops, roofs or the sea; hard impacts make you tumble.
