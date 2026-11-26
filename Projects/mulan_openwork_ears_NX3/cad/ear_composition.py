"""Place the supplied foreground and dragon relative to the engraved NX3 rim."""

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates
from shapely import affinity, contains_xy
from shapely.geometry import box
from svgpathtools import parse_path

from hand_relief import continuous_trio
from lithograph import Artwork, GRID_MM, height_mesh, source_layers


# Registered to Brighter-dragon.jpg. The lowest path includes the rocket
# directly beneath the dragon's feet and excludes the neighboring fireworks.
DRAGON_OUTLINES = (
    """M 0 222 C 39 148 105 95 167 76 Q 201 66 227 68
    Q 245 52 255 61 Q 265 71 268 63 Q 272 51 252 52
    Q 263 44 271 49 Q 280 52 276 67 L 284 92
    C 299 132 303 152 334 179 Q 352 170 373 180
    Q 402 152 426 128 L 447 80 Q 442 67 444 56
    Q 447 45 466 51 Q 451 51 451 64 Q 454 72 465 63
    Q 480 54 497 69 C 565 68 620 100 663 150
    C 688 179 707 221 711 269 Q 684 220 653 219
    C 621 214 607 245 605 280 Q 570 253 546 262
    Q 525 267 514 300 Q 485 280 459 285 Q 494 303 513 336
    Q 472 315 447 358 Q 413 343 403 360 L 403 383 L 320 390
    Q 324 339 283 350 Q 277 321 228 328 Q 244 315 266 299
    Q 231 281 194 304 Q 187 275 171 266 C 148 249 123 258 105 275
    C 108 235 79 204 50 201 Q 24 197 0 222 Z""",
    """M 333 179 Q 322 152 336 133 L 347 124 Q 343 141 341 162
    L 339 178 Z M 366 176 Q 377 145 369 123 Q 383 133 382 145
    Q 387 159 375 180 Z""",
    """M 320 197 Q 315 221 326 242 Q 337 254 352 252
    Q 375 281 373 297 Q 369 311 348 327
    Q 326 348 325 373 L 297 387 Q 298 394 309 400
    L 282 403 L 270 424 Q 293 411 313 413 L 330 402
    Q 353 406 379 411 L 402 426 Q 424 427 446 438 L 435 412
    L 413 400 Q 403 392 403 364 L 381 363 Q 352 351 356 335
    C 365 322 392 309 400 292 Q 410 274 392 251 L 375 223
    Q 376 208 380 195 Z""",
    """M 403 379 Q 458 359 477 355 Q 502 354 525 359
    Q 543 359 557 341 Q 573 320 584 326 Q 594 328 595 344
    Q 585 331 574 334 Q 560 339 548 355 Q 539 367 525 367
    Q 489 361 463 376 Q 431 394 408 397 Z""",
    """M 229 510 Q 243 493 258 480 Q 255 451 272 432
    C 292 411 319 400 349 400 C 388 399 418 416 436 447
    Q 453 477 451 505 L 229 510 Z""",
)


def traced_feature(size, paths, width=None):
    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    for outline in paths:
        for contour in parse_path(outline).continuous_subpaths():
            vertices = []
            for p in contour:
                count = max(2, math.ceil(p.length()/1.1))
                vertices.extend((z.real, z.imag)
                                for z in (p.point(i/count) for i in range(count)))
            endpoint = contour[-1].end
            vertices.append((endpoint.real,endpoint.imag))
            if width is None:
                draw.polygon(vertices,fill=255)
            else:
                draw.line(vertices,fill=255,width=width,joint="curve")
    return np.asarray(mask) > 0


def dragon_matte(image):
    assert image.size == (736, 552), "Dragon trace is registered to the supplied frame."
    color = gaussian_filter(np.asarray(image.convert("RGB"), dtype=float)/255, (.66,.66,0))
    red, green, blue = np.moveaxis(color,-1,0)
    sky = (blue > .57) & (blue-red > .42) & (blue-green > .26)
    def alpha(paths):
        distance = distance_transform_edt(traced_feature(image.size,paths))
        return np.clip((distance-np.where(sky,2.0,.7))/1.15,0,1)
    return color,alpha(DRAGON_OUTLINES[:-1]),alpha(DRAGON_OUTLINES[-1:])


def dragon_terraces(size, source_color):
    """Assign relief heights and align the revised facial paint boundaries."""
    surface = np.full((size[1],size[0]),.72)
    color = source_color.copy()

    def level(height, paths, width=None, within=1., paint=None):
        mask = traced_feature(size,paths,width)
        # A short chamfer at the edge leaves room for several vertical
        # print layers while maintaining the flat interior of each terrace.
        signed = distance_transform_edt(mask)-distance_transform_edt(~mask)
        weight = np.clip((signed+1.75)/3.5,0,1)*within
        surface[:] += weight*(height-surface)
        if paint is not None:
            color[:] += weight[:,:,None]*(np.asarray(paint)/255.-color)
        return weight

    # Alternate the broad wing panels, then set their thin red ribs on a
    # third level. Heights are measured above the uncut lithograph plane.
    level(1.19, (
        "M 0 222 C 39 148 105 95 167 76 Q 201 66 227 68 L 229 108 C 143 82 62 158 0 222 Z",
        "M 106 270 Q 151 172 213 161 Q 225 158 242 155 Q 253 184 242 222 Q 213 247 194 302 C 174 264 146 248 106 270 Z",
        "M 233 324 Q 282 276 350 265 L 357 282 Q 321 308 306 346 Q 287 348 283 350 Q 268 319 233 324 Z",
        "M 484 105 L 485 69 C 568 67 625 105 663 150 Q 700 198 710 268 Q 649 162 598 139 Q 541 86 484 105 Z",
        "M 488 168 Q 552 180 602 274 Q 577 255 548 261 Q 522 272 514 297 Q 495 246 463 229 Q 485 217 488 168 Z",
        "M 391 274 Q 457 285 510 334 Q 469 317 447 356 Q 420 311 391 274 Z",
    ))
    level(1.72, (
        "M 3 218 C 62 158 143 82 229 108",
        "M 107 264 Q 150 173 212 161",
        "M 197 295 Q 214 247 240 225",
        "M 230 323 Q 286 265 351 264",
        "M 485 107 C 565 78 648 148 702 250",
        "M 490 167 Q 563 190 602 272",
        "M 463 231 Q 499 250 514 295",
        "M 390 275 Q 418 306 443 353",
    ),9)
    # The mane is distinct from the wing membranes. Carve curls into it.
    mane = level(1.06, (
        "M 232 145 C 216 133 225 102 246 96 Q 274 86 283 111 Q 293 133 274 145 C 301 181 303 208 320 221 Q 328 248 305 258 Q 284 271 275 246 Q 272 236 274 227 C 237 233 216 214 215 188 Q 212 161 232 145 Z",
        "M 444 148 C 428 138 435 107 454 99 Q 488 93 491 121 Q 497 142 479 151 C 494 166 497 199 479 220 Q 464 231 437 229 C 435 249 427 261 409 258 Q 386 251 384 233 Q 410 220 421 182 Z",
    ))
    level(.73, (
        "M 257 128 Q 243 129 241 117 Q 240 108 252 107 Q 266 107 268 121",
        "M 292 242 Q 286 231 295 225 Q 307 220 313 230",
        "M 459 113 Q 473 111 476 121 Q 478 132 468 133",
        "M 414 246 Q 424 241 422 232 Q 419 222 407 227",
    ),7,mane)

    # Establish one low red silhouette under the alternating gold scales.
    level(1.29, (
        "M 349 244 Q 369 238 381 255 C 399 271 406 293 397 308 C 389 326 363 337 355 352 Q 345 369 363 383 L 391 394 L 384 411 Q 354 409 333 394 C 313 376 321 349 337 331 C 350 316 369 305 370 292 Q 366 272 349 244 Z",
    ))
    belly = level(1.65, (
        "M 351 248 Q 362 241 371 252 C 382 269 395 292 386 309 C 374 327 350 341 345 358 Q 337 376 353 389 Q 362 399 380 399 L 377 407 Q 356 404 339 396 C 319 383 321 356 335 336 Q 345 324 363 310 Q 375 300 373 289 Q 367 266 351 248 Z",
    ))
    level(2.16, (
        "M 345 246 Q 369 239 382 254 L 390 275 Q 373 285 356 273 Z",
        "M 368 299 Q 378 303 395 306 L 376 328 Q 361 337 342 347 L 331 341 Z",
        "M 320 365 Q 333 371 347 364 L 365 388 L 388 398 Q 366 402 346 396 L 325 387 Z",
    ),within=belly)
    level(1.2, (
        "M 354 255 Q 367 259 377 256",
        "M 367 278 Q 382 281 390 277",
        "M 369 305 Q 382 306 390 310",
        "M 337 340 Q 347 341 357 344",
        "M 326 379 Q 340 382 350 378",
        "M 347 398 Q 362 399 380 394",
    ),6,belly)

    # Narrow the red temple above each tuft and keep the broad forehead.
    level(1.79, (
        "M 324.7 185.2 Q 330.4 177.7 339.1 174.6 Q 352 167.8 365.8 175.6 Q 374.2 177.8 376.1 182.8 L 376.1 194 Q 369.8 203 352 206 Q 333.4 205 326.2 198.9 Z",
    ),paint=(89,30,64))

    # The jaw, tufts, and tooth outline trace the registered face crop.
    jaw = level(1.77, (
        "M 332.2 195.8 Q 340.5 200.3 349.5 200.5 Q 359 200.3 364.8 196.9 Q 367 201.3 367.5 207.3 Q 366.7 213.5 369.1 219.3 Q 371.7 225 372.8 231.3 L 374.6 239.8 Q 371.5 241.7 367.7 244.8 Q 363.5 248.2 355.6 249.7 Q 348.4 250.8 342 248.7 Q 334.6 246.6 328 242.4 L 326.9 240.4 Q 329.3 237.8 328.3 234.6 L 329.3 230 Q 328.8 226 328.5 222.4 Q 330.1 215.6 329.6 211.2 Q 328.8 205.7 332.2 195.8 Z",
    ),paint=(171,47,82))
    level(1.48, (
        "M 334.6 199 Q 330.4 199.5 327.5 203.9 Q 325.1 208.6 324 212 L 327.7 210.2 Q 326.2 212.8 324.3 214.9 L 329.6 212.2 Q 329.1 215.9 330.7 218.8 Q 333.6 214.3 334.4 210.4 Q 336.2 203.1 334.6 199 Z",
        "M 365.1 198.4 Q 369.9 198.4 374.1 203.1 Q 377.5 207 378.9 210.4 L 375.2 208.3 Q 377.3 211.7 377.8 215.1 L 373.6 212.5 L 376 217.5 Q 372.5 219 370.4 216.4 Q 367.2 211.5 365.9 207.6 Z",
    ),paint=(112,36,73))
    level(1.91, (
        "M 332.8 200.5 Q 329.9 201.3 328 204.7 L 326.4 209.1 L 329.9 207 Q 329.1 210.9 327.7 212.8 L 330.9 210.7 L 330.9 214.9 Q 333.8 209.9 333.8 204.7 Z",
        "M 367.7 201.1 Q 372.5 202.1 375.7 207.3 L 373 206.5 Q 375.2 210.2 375.7 212.8 L 372.5 210.7 L 373.8 214.9 Q 369.6 213.3 368.8 208.9 Z",
    ),paint=(150,48,87))
    level(1.12, (
        "M 334.9 200.8 Q 335.4 207.3 332.5 213.8",
        "M 365.4 200.8 Q 366.4 206.3 369.3 212.8",
    ),5,paint=(69,21,57))

    # Thin the outer wraps without moving or shallowing the eye sockets.
    level(1.97, (
        "M 325 184.3 Q 336.4 185.2 349 195 L 348.8 199.4 Q 342.4 202.4 333.2 200.1 Q 326.3 197.2 325 191.8 Z",
        "M 351.8 195.4 Q 363.8 185.1 375.9 183.5 Q 377.2 194.1 369.3 199.9 Q 360.7 202.6 351.8 199.4 Z",
    ),paint=(100,32,66))
    level(2.12, (
        "M 326.5 184.3 Q 338 186.4 346.8 194.2 L 346.8 197.8 Q 335.1 193 327.1 189.4 Z",
        "M 353.6 194.2 Q 363.2 186.4 374.5 184.6 L 373.5 190 Q 363.5 193 353.6 197.8 Z",
    ),paint=(99,32,62))
    eyes = level(1.31, (
        "M 326.9 187 C 336.2 188.8 340.9 193 347.5 196.6 Q 340.2 200.2 332.9 196.6 Q 327.6 193.6 326.9 187 Z",
        "M 352.9 196.6 Q 364.2 189.4 374.1 186.4 Q 372.8 194.2 366.9 197.2 Q 359.6 200.2 352.9 196.6 Z",
    ),paint=(250,236,196))
    level(1.31, ("M 334.8 190 L 338.2 194.8","M 366.9 190 L 362.8 194.8"),5,eyes,paint=(48,23,45))
    nose = level(2.48, (
        "M 332 210 Q 341 202 351 207 Q 362 211 360 222 Q 354 232 342 232 Q 331 227 330 220 Q 328 215 332 210 Z",
    ),paint=(100,29,69))
    level(1.83, ("M 333 219 L 335 222", "M 355 218 L 355 222"),6,nose,paint=(56,21,52))

    # Trace the scooped top, offset right corner, and curved tooth row
    # from the registered detail. Keep the interior blank for painting.
    level(1.94, (
        "M 328.3 224.5 C 333.3 227.1 338.9 229.7 344.7 229.4 Q 354 229.2 358.7 225.5 L 361.1 224 Q 364.8 225.3 365.9 228.9 Q 365.4 231.3 367.5 234.9 Q 368.8 238.5 369.9 240.9 Q 365.4 241.1 361.4 243.8 Q 353.7 247.1 345.8 246.6 Q 336.8 245.6 327.2 241.9 Q 328.5 238.8 327.7 235.9 Q 329.3 232.6 328.3 229.2 Z",
    ),within=jaw,paint=(193,46,84))
    level(2.35, (
        "M 330.4 226.8 C 333.3 229.7 337 230.5 341 230.5 Q 345.5 232.3 350 230.7 Q 355 230.2 359 227.6 Q 360.3 226.8 361.1 225.8 Q 363 226.3 364 228.1 L 364 229.7 Q 365.9 230.7 364.6 232.6 L 365.4 235.2 L 367.2 238.3 Q 365.6 238 363.5 239.3 Q 358.2 241.7 351.9 243 Q 344.7 244.8 338.6 243.5 Q 334.4 242.4 331.2 240.6 L 329.9 239.3 Q 331.5 237.5 331.5 235.9 Q 329.9 234.9 330.9 233.1 Q 332.8 231.5 332 229.7 Z",
    ),paint=(212,245,224))
    level(1.96, (
        "M 327 214 Q 316 220 308 232 Q 300 244 292 245",
        "M 365 217 Q 378 224 386 236 Q 392 248 401 251",
        "M 335 172 Q 330 157 336 142",
        "M 371 174 Q 379 154 374 141",
    ),9)
    return surface,color


def sample(array, u, v, mode="constant"):
    coords = [v,u]
    if array.ndim == 3:
        return np.stack([map_coordinates(array[:,:,i], coords, order=1, mode=mode)
                         for i in range(3)],axis=-1)
    return map_coordinates(array,coords,order=1,mode=mode)


def elongated_face_rows(u, v):
    """Lengthen the muzzle, grin and chin while anchoring the eyes and neck."""
    source = (162., 176., 192., 208., 227., 247., 263., 282., 307., 332.)
    stretched = (162., 176., 193., 213., 239., 269., 285., 300., 316., 332.)
    displacement = np.interp(v,stretched,source)-v
    within_rows = (v > stretched[0]) & (v < stretched[-1])
    # Keep the middle of the face at full stretch. Fade the displacement
    # before the outer wing panels so they retain their shapes.
    weight = np.minimum(np.clip((u-273.)/44.,0.,1.),np.clip((434.-u)/43.,0.,1.))
    weight = weight*weight*(3.-2.*weight)
    return v + np.where(within_rows,displacement*weight,0.)


def crop_upright(x, y, angle):
    angle = math.radians(angle)
    ca, sa = math.cos(angle), math.sin(angle)
    return ca*x-sa*(y-38.79776), sa*x+ca*(y-38.79776)


class Composition:
    def __init__(self, picture, interior, index, dragon=None):
        self.index = index
        self.background = np.array([.13,.18,.43])
        self.base_safe = interior.buffer(.24 if index == 0 else -.48)
        self.safe = self.base_safe
        minx, miny, maxx, maxy = self.safe.bounds
        self.grid_x = np.arange(minx-2*GRID_MM,maxx+3*GRID_MM,GRID_MM)
        self.grid_y = np.arange(miny-2*GRID_MM,maxy+3*GRID_MM,GRID_MM)
        x,y = np.meshgrid(self.grid_x,self.grid_y)
        if index == 0:
            h, colors = self.trio(picture, interior, x, y)
            inside = contains_xy(self.safe,x,y)
            self.depth = h*inside
            self.color = self.background+(colors-self.background)*inside[:,:,None]
        else:
            # Keep the exact previous grid and Mulan's crop. Permit the
            # rocket alone to overlap the inner wall in its lower section.
            zone = affinity.rotate(box(-35,-32,-8,-7.0),40,origin=(0,0))
            self.rocket_zone = affinity.translate(zone,yoff=38.79776).intersection(interior.buffer(.26))
            self.safe = self.base_safe.union(self.rocket_zone)
            self.depth, self.color = self.mulan_and_dragon(picture, dragon, x, y)
        self.x,self.y = x,y

    def trio(self, picture, interior, x, y):
        source = Artwork(picture, interior, 0)
        self.foreground_scale = source.scale * source.alpha.shape[1] / picture.width
        u,v = source.photo_coordinates(x,y)
        a = sample(source.alpha,u,v)
        h = sample(source.depth,u,v)
        rgb = sample(source.color,u,v,"nearest")
        a,h,rgb = continuous_trio(a,h,rgb,u,v,source.alpha.shape)
        colors = self.background*(1-a[:,:,None])+rgb*a[:,:,None]
        return h,colors

    def mulan_and_dragon(self, picture, dragon, x, y):
        upright_x,upright_y = crop_upright(x,y,-40)
        # Mount the larger head-and-tunic crop in front. The inner rim
        # provides the diagonal crop through the lower garment.
        self.foreground_scale = .075
        u = upright_x/self.foreground_scale + 598
        v = (37.2-upright_y)/self.foreground_scale + 75
        front_color, front_alpha, front_depth = source_layers(picture)
        a = sample(front_alpha,u,v)
        shade = sample(front_depth,u,v)
        color = sample(front_color,u,v,"nearest")
        front = a*.83 + .77*shade + a*.53
        base = contains_xy(self.base_safe,x,y)
        taper = np.minimum(distance_transform_edt(base)*GRID_MM/.48,1.)
        # Keep the dragon in the previous position, to the left of Mulan.
        du = (upright_x+20.2)/.109 + 350
        raw_v = (17.4-upright_y)/.097 + 194
        dv = np.where(raw_v > 403, 403+(raw_v-403)/1.48, raw_v)
        dc,da,rocket_alpha = dragon_matte(dragon)
        face_v = elongated_face_rows(du,dv)
        d = sample(da,du,face_v)
        relief_map,dragon_color = dragon_terraces(dragon.size,dc)
        rgb_d = sample(dragon_color,du,face_v,"nearest")
        dragon_relief = d*sample(relief_map,du,face_v)

        rv = self.rocket_rows(upright_x,upright_y,dv)
        rocket_gate = np.maximum(taper,contains_xy(self.rocket_zone,x,y))
        rocket = sample(rocket_alpha,du,rv)*rocket_gate
        rocket_color = sample(dc,du,rv,"nearest")
        rocket_luma = rocket_color @ np.array([.25,.56,.19])
        rocket_relief = rocket*(.56+.84*rocket_luma)
        back_color = self.background*(1-rocket[:,:,None])+rocket_color*rocket[:,:,None]
        dragon_show = (d*taper)[:,:,None]
        back_color = back_color*(1-dragon_show)+rgb_d*dragon_show
        foreground_show = (a*taper)[:,:,None]
        paint = back_color*(1-foreground_show)+color*foreground_show
        relief = np.maximum(dragon_relief*taper,rocket_relief)*(1-a)+front*taper
        return relief,paint

    def rocket_rows(self, upright_x, upright_y, previous_rows):
        """Continue the lower rocket body to the rim at each column."""
        screen_x = np.arange(-35.,-7.9,GRID_MM)
        screen_y = np.arange(-32.,-6.9,GRID_MM)
        x,y = np.meshgrid(screen_x,screen_y)
        angle = math.radians(40)
        ca,sa = math.cos(angle),math.sin(angle)
        hits = contains_xy(self.rocket_zone,ca*x-sa*y,sa*x+ca*y+38.79776)
        have_floor = np.any(hits,axis=0)
        floor_columns = screen_x[have_floor]
        floor_rows = screen_y[np.argmax(hits[:,have_floor],axis=0)]
        floor = np.interp(upright_x,floor_columns,floor_rows)
        anchor = 17.4-.097*(403+(451-403)*1.48-194)
        fraction = (anchor-upright_y)/np.maximum(anchor-floor,.30)
        stretched = 451+48*np.clip(fraction,0,1.04)
        active = (upright_y < anchor)&(floor < anchor-.3)
        return np.where(active,stretched,previous_rows)

    def mesh(self):
        return height_mesh(self.x,self.y,self.depth), self.depth

    def color_at(self, x, y):
        u = (x-self.grid_x[0])/GRID_MM
        v = (y-self.grid_y[0])/GRID_MM
        return (255*sample(self.color,u,v,"nearest")).clip(0,255)

    def placed_image(self):
        """Show the registered colors in mounted orientation for review."""
        angle = 40 if self.index == 0 else -40
        ca,sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        xs,ys = np.meshgrid(np.linspace(-47.,47.,760),np.linspace(47.,-47.,760))
        x = ca*xs+sa*ys
        y = -sa*xs+ca*ys+38.79776
        mask = contains_xy(self.safe,x,y)
        output = np.zeros((*x.shape,4),dtype=np.uint8)
        output[:,:,:3] = self.color_at(x,y)
        output[:,:,3] = mask*255
        return Image.fromarray(output)
