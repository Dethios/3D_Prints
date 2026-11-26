# Illustration sources

## Fan trio

The built-in image generator produced fan-trio-illustration.png using the supplied fan photo and the NX3 interior outline. The prompt was:

> Create a NEW clean 2D color illustration of the three disguised palace guards with fans from Disney's animated Mulan, for the LEFT ear of a paintable NX3 headband. Input 1 is the original photo ONLY for character identity, recognizable features, color, position of hands, and fan arrangement. Input 2 is a CAD placement guide ONLY: the light beige shape shows the available canvas, rounded top and left, sharply rising diagonal lower-right edge. Use the maximum available width and height. Do not draw the guide, backing, gold border, or anything from the photographed packaging. Deliver one square, genuinely transparent RGBA image, subject only. Flat cel colors, clean confident dark outlines, a small number of broad contiguous paint regions, generous bold details, no texture, lighting, shadows, bevels, glints or photorealism.
> Match the original recognizably: blue-robed guard at top with black hair, pale painted face and raised left hand, holding a broad turquoise blue pleated fan; square-faced black-browed guard in the foreground, red cap bands and red clothing with a wide vivid orange folding fan and visible hand; third pale-faced guard to the right behind a saffron yellow folding fan with the distinct tall black oval hair ornament/topknot loop rising above his head. Exactly these three faces and three open folding fans. Use bold fan ribs, clean expressive eyes and recognizable hair outlines. Pack them together in the broad area from upper left through center and right, use the foreground red garment and lower fan edges to occupy the deeper lower-left area. Let the yellow garment and interlocking fan and sleeve contours resolve along the rising diagonal, with all faces, fans and clothing wholly inside the guide. Extend the overlapping clothing and the fans into a coherent lower edge; omit ALL flowers, petals, botanical decoration, background, rings, border, typography and logos. No cropping. Show the illustration from directly in front. This is the new master art for manufacturing, not a mockup.

## Mulan

The image generator returned an output moderation error on both Mulan attempts. The Mulan artwork was drawn as a new SVG from the supplied medallion photo and rasterized with cad/render_illustration.py. The final attempted prompt is recorded for provenance:

> Create a fresh wholesome animation-cel illustration of adult Mulan in a fully covered historical blue tunic and long sleeves, for a personal painted decorative medallion. Use input photo 1 as a character and costume reference only, and the pale region in input image 2 as a placement guide only. The output is the isolated flat-color artwork as a transparent PNG. Do not render the guide itself. Closely preserve the expression, flying black hair, pale blue sleeves, navy vest, red collar, red sash and original body pose. One hand is extended to the left in the same expressive gesture as in the photo. The other hand holds a stylized ornamental silver film-prop blade horizontally above her head, following the original composition. Keep the ornamental silhouette simple and all parts inside the pale region. As the bottom of the illustration, extend the tunic and sash naturally to form a broad curved blue hem that fills the available area in the lower right of the guide, so the illustration looks complete. Use no flowers, plants, border, wrapping, text, background, texture or lighting effects. Use smooth crisp lines and broad hand-paintable cel color blocks. Large composition fitted inside the guide. Single subject with her ornamental prop only. Front orthographic view of the flat drawing and transparent negative space.


## Supplied replacement and dragon

The current right ear uses mulan-illustration2.png as the foreground and
mushu-dragon-reference.png as the lower relief behind it. Both files were
supplied by the user. The artwork setup in cad/ear_composition.py crops the
figure to the actual recess and masks the winged dragon out of the frame.
The prior SVG is retained as an earlier revision.

## Brighter dragon and corrected trio hands

The right relief uses Brighter-dragon.jpg. The matte includes the rocket beneath the dragon's feet. The Mulan foreground is still the supplied mulan-illustration2.png.

The built-in image generator produced fan-trio-hands-corrected.png from the prior trio artwork, the supplied Tro-reference.jpg, and the hand close-up. These were the two edit prompts.

> Edit the first image with surgical precision. Preserve the exact three characters, their faces, expressions, their positions and relative scale, costumes, vivid flat cel colors, line weight, the full shapes and positions of the three turquoise, orange and yellow fans, the tall black loop ornament above the yellow guard, the diagonal perimeter and the genuine transparent background. Only retouch these three hands. The second reference photo is for original poses and costume only. The third close-up shows the hand areas to correct.
> 1. Red figure's raised hand at the far lower left: give him a clearly distinguishable thumb plus four curled fingers. Retain the loose curling gesture but add a visible small rounded pinky on the outside left edge below the ring finger. Use five real digit shapes total. Keep the red sleeve below.
> 2. Red figure's hand at bottom center gripping the orange fan: make a natural grip with a thumb wrapped around the fan hinge, then four cuff-side curled fingertips of descending size, including a small fourth/pinky below the other three. Draw four compact stacked finger ridges, with a discreet rounded lowest pinky above the wrist and no extra digits. Keep hand away from the tip of the diagonal crop, preserve his red sleeve and the fan.
> 3. Yellow figure's visible hand along the lower right part of the yellow fan: shorten the fingers and palm by about one third. Natural compact proportions, visibly separate the fingers, retain a graceful relaxed hand pose on the fan; fill the vacated upper area with the correct yellow fan panels and lower space with the yellow sleeve as appropriate. Keep the red figure's hand a distinct separate shape. No other changes. One clean square transparent artwork, no frame or text.

> Retouch ONLY the red-robed guard's lower middle hand that clutches the orange folding fan's hinge, at about x=450 y=1090 of the supplied transparent illustration. Preserve the entire rest of this exact flat cel PNG, including the revised raised red hand to the left, the compact yellow hand, the faces, outlines, fan shapes, colors and alpha. Keep transparent background.
> The current lower gripping contour reads as thumb plus only three rounded stacked fingertips on the viewer's left edge. Add the missing FOURTH curled fingertip, the little pinky, as a distinct small rounded lobe directly BELOW the current lowest fingertip and ABOVE the inside bend of the wrist. The separate thumb stays spread across the upper fan base. The outside edge of the grip now has FOUR compact finger lobes stacked below the thumb, each separated by a clean black contour line, with the little finger smallest and distinct rather than fused into palm. Do not lengthen the wrist or enlarge the hand. This is a tiny localized anatomy correction. Preserve the rest pixel-for-pixel as closely as possible.

