/*
 * The gameplay background, as YataiDON draws it.
 *
 * Its background is not one picture. It is a band above the lanes that
 * scrolls and lights up when you clear, five standard scenes and four
 * fever ones that are each built differently from the others, dancers
 * that arrive as the gauge fills, and small characters that run across
 * on every hit. All of it is declared in the skin -- where each layer
 * sits, how many frames it has and in what order they play -- and
 * driven by scripts.
 *
 * So this is a port of those scripts rather than an impression of them,
 * and the skin's own data comes in through the manifest: positions,
 * frame orders, and the animation declarations that bganim.js builds.
 * Where a number appears here it is because it is written in the script
 * rather than the data.
 *
 * Everything is optional. The art is private, so the public build has no
 * manifest, builds nothing and draws nothing: the game runs, it simply
 * has a plain background.
 *
 * One difference from YataiDON, and it is geometry rather than choice.
 * Its note lanes end at y=360 of a 1280x720 screen and taiko-web's end
 * at 322, so the band above the lanes is repeated downwards to cover the
 * gap. Every other layer is drawn where the skin puts it.
 */

/*
 * A folder of the skin's art, and everything the game needs to know to
 * draw a layer out of it: where it goes, how big it is drawn, which
 * frame of the strip that is, and what to do with the transform.
 *
 * The parameters are YataiDON's draw_texture parameters, and they mean
 * what they mean there: x and y are offsets from the position the skin
 * gives, not absolute; index picks between positions when a layer has
 * several; x2 and y2 adjust the drawn size.
 */
class BgTex{
	constructor(manifest, folder){
		this.manifest = manifest
		this.prefix = "yatai_" + folder.replace(/\//g, "_")
	}
	
	name(key){
		return this.prefix + "_" + key
	}
	
	info(key){
		return this.manifest.assets[this.name(key)] || null
	}
	
	has(key){
		return !!this.info(key)
	}
	
	// What a frame index means to an animation: the length of the play
	// order where there is one, and the number of frames where there is
	// not.
	frameCount(key){
		var entry = this.info(key)
		if(!entry){
			return 1
		}
		return entry.order ? entry.order.length : entry.frames
	}
	
	draw(ctx, key, params){
		var entry = this.info(key)
		if(!entry){
			return
		}
		var img = assets.image[this.name(key)]
		if(!img || !img.naturalWidth){
			return
		}
		params = params || {}
		var alpha = params.fade === undefined ? 1 : params.fade
		if(alpha <= 0){
			return
		}
		var pos = entry.pos[params.index || 0] || entry.pos[0]
		var scale = params.scale === undefined ? 1 : params.scale
		var w = pos.x2 * scale + (params.x2 || 0)
		var h = pos.y2 * scale + (params.y2 || 0)
		var x = pos.x + (params.x || 0)
		var y = pos.y + (params.y || 0)
		if(params.center){
			x += (entry.w - entry.w * scale) / 2
			y += (entry.h - entry.h * scale) / 2
		}
		
		var frame = Math.floor(params.frame || 0)
		if(entry.order){
			frame = entry.order[((frame % entry.order.length) + entry.order.length) % entry.order.length]
		}
		frame = Math.max(0, Math.min(entry.frames - 1, frame))
		
		ctx.save()
		if(alpha < 1){
			ctx.globalAlpha *= alpha
		}
		ctx.translate(x, y)
		if(params.rotation){
			ctx.rotate(params.rotation * Math.PI / 180)
		}
		// The origin is where the position lands and what a rotation
		// turns around, so the drawn rectangle starts back from it.
		if(params.origin){
			ctx.translate(-params.origin[0], -params.origin[1])
		}
		if(params.mirror === "horizontal"){
			ctx.translate(w, 0)
			ctx.scale(-1, 1)
		}
		ctx.drawImage(img, frame * entry.w, 0, entry.w, entry.h, 0, 0, w, h)
		ctx.restore()
	}
}

/*
 * The band above the note lanes.
 *
 * Its art has two frames and they are not an animation: frame 0 is the
 * band, frame 1 is the same band lit up, and clearing fades the second
 * over the first in 150ms. Reading them as a loop is what made the band
 * flash.
 *
 * The band also scrolls -- one tile every three seconds, forever -- and
 * every set moves its overlay differently, which is what the six
 * variants below are.
 */
class DonBG{
	constructor(background, index, half){
		this.background = background
		this.tex = background.tex("donbg/" + index + "_" + half)
		this.manifest = background.manifest
		var info = this.tex.info("background")
		this.bgWidth = info ? info.w : 328
		this.bgHeight = info ? info.h : 184
		this.move = new BgMove(3000, {total_distance: -this.bgWidth, loop: true})
		this.move.start()
		this.isClear = false
		this.clearFade = BgAnim.get(this.manifest, "1")
	}
	
	static create(background, index, half){
		var variants = [DonBG0, DonBG1, DonBG2, DonBG3, DonBG4, DonBG5]
		var variant = variants[index] || DonBG0
		return new variant(background, index, half)
	}
	
	setClear(isClear){
		if(isClear && !this.isClear){
			this.isClear = true
			this.clearFade.start()
		}
		if(!isClear && this.isClear){
			this.isClear = false
			this.clearFade.reset()
		}
	}
	
	update(ms){
		this.move.update(ms)
		this.clearFade.update(ms)
	}
	
	/*
	 * Where a tiled layer goes, across the whole window.
	 *
	 * The skin counts its tiles for a 1280-wide screen -- five of the
	 * band, thirty-one of the footer. The window is usually wider than
	 * the frame the art is drawn for, so the count comes from the width
	 * instead and the phase comes from the scroll, which is the same
	 * thing the fixed counts were.
	 */
	tiles(width, offset){
		var span = this.background.span
		var out = []
		if(!(width > 0)){
			return out
		}
		var x = Math.floor((span.left - offset) / width) * width + offset
		for(; x < span.right; x += width){
			out.push(x)
		}
		return out
	}
	
	/*
	 * taiko-web's lanes stop 38px higher than YataiDON's, so the band is
	 * repeated downwards until it reaches them. The decoration on top of
	 * it is drawn once, where the skin puts it.
	 */
	drawBand(ctx, fade, y, frame){
		var rows = Math.max(1, Math.ceil(GameBackground.TOP / this.bgHeight))
		var xs = this.tiles(this.bgWidth, this.move.attribute)
		for(var row = 0; row < rows; row++){
			for(var i = 0; i < xs.length; i++){
				this.tex.draw(ctx, "background", {
					frame: frame,
					fade: fade,
					x: xs[i],
					y: y + row * this.bgHeight
				})
			}
		}
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
	}
	
	draw(ctx, y){
		y = y || 0
		ctx.save()
		// Repeating the band leaves it a little longer than the gap it
		// fills; the scene below it should stay the top layer there.
		ctx.beginPath()
		ctx.rect(this.background.span.left, 0, this.background.span.width, GameBackground.TOP)
		ctx.clip()
		this.drawTextures(ctx, 1, y, 0)
		if(this.isClear){
			this.drawTextures(ctx, this.clearFade.attribute, y, 1)
		}
		ctx.restore()
	}
}

// Set 0: a bobbing overlay and a footer strip tiled right across.
class DonBG0 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.overlayMove = BgAnim.get(this.manifest, "2")
		this.overlayWidth = (this.tex.info("overlay") || {w: 1}).w
		this.footerWidth = (this.tex.info("footer") || {w: 1}).w
	}
	
	update(ms){
		super.update(ms)
		this.overlayMove.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		var overlay = this.tiles(this.overlayWidth,
			this.move.attribute * (this.overlayWidth / this.bgWidth))
		for(var i = 0; i < overlay.length; i++){
			this.tex.draw(ctx, "overlay", {
				frame: frame, fade: fade, x: overlay[i],
				y: y + this.overlayMove.attribute
			})
		}
		var footer = this.tiles(this.footerWidth,
			this.move.attribute * (this.footerWidth / this.bgWidth) * 3)
		for(var i = 0; i < footer.length; i++){
			this.tex.draw(ctx, "footer", {
				frame: frame, fade: fade, x: footer[i],
				y: y + this.overlayMove.attribute
			})
		}
	}
}

// Set 1: the same, slower, and the overlay rides the band exactly.
class DonBG1 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.overlayMove = BgAnim.get(this.manifest, "3")
		this.overlayWidth = (this.tex.info("overlay") || {w: 1}).w
	}
	
	update(ms){
		super.update(ms)
		this.overlayMove.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		var overlay = this.tiles(this.overlayWidth, this.move.attribute)
		for(var i = 0; i < overlay.length; i++){
			this.tex.draw(ctx, "overlay", {
				frame: frame, fade: fade, x: overlay[i],
				y: y + this.overlayMove.attribute
			})
		}
	}
}

// Set 2: a half-width band, so twice as many tiles, and an overlay that
// bounces on top of two drifts running one behind the other.
class DonBG2 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.bounceUp = BgAnim.get(this.manifest, "4")
		this.bounceDown = BgAnim.get(this.manifest, "5")
		this.bounceUp.start()
		this.bounceDown.start()
		this.overlayMove = BgAnim.get(this.manifest, "6")
		this.overlayMove2 = BgAnim.get(this.manifest, "7")
		this.overlayWidth = (this.tex.info("overlay") || {w: 1}).w
	}
	
	update(ms){
		super.update(ms)
		this.bounceUp.update(ms)
		this.bounceDown.update(ms)
		if(this.bounceDown.isFinished){
			this.bounceUp.restart()
			this.bounceDown.restart()
		}
		this.overlayMove.update(ms)
		this.overlayMove2.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		var offset = this.bounceUp.attribute - this.bounceDown.attribute +
			this.overlayMove.attribute + this.overlayMove2.attribute
		var overlay = this.tiles(this.overlayWidth, this.move.attribute * 2)
		for(var i = 0; i < overlay.length; i++){
			this.tex.draw(ctx, "overlay", {
				frame: frame, fade: fade, x: overlay[i], y: y + offset
			})
		}
	}
}

// Set 3: as set 0 without the footer.
class DonBG3 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.overlayMove = BgAnim.get(this.manifest, "2")
		this.overlayWidth = (this.tex.info("overlay") || {w: 1}).w
	}
	
	update(ms){
		super.update(ms)
		this.overlayMove.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		var overlay = this.tiles(this.overlayWidth, this.move.attribute)
		for(var i = 0; i < overlay.length; i++){
			this.tex.draw(ctx, "overlay", {
				frame: frame, fade: fade, x: overlay[i],
				y: y + this.overlayMove.attribute
			})
		}
	}
}

// Set 4: the bounce again, with a slow drift subtracted from it.
class DonBG4 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.bounceUp = BgAnim.get(this.manifest, "4")
		this.bounceDown = BgAnim.get(this.manifest, "5")
		this.bounceUp.start()
		this.bounceDown.start()
		this.adjust = BgAnim.get(this.manifest, "8")
	}
	
	update(ms){
		super.update(ms)
		this.bounceUp.update(ms)
		this.bounceDown.update(ms)
		if(this.bounceDown.isFinished){
			this.bounceUp.restart()
			this.bounceDown.restart()
		}
		this.adjust.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		var offset = this.bounceUp.attribute - this.bounceDown.attribute - this.adjust.attribute
		var overlay = this.tiles(this.bgWidth, this.move.attribute)
		for(var i = 0; i < overlay.length; i++){
			this.tex.draw(ctx, "overlay", {
				frame: frame, fade: fade, x: overlay[i], y: y + offset
			})
		}
	}
}

// Set 5: two overlays, the front one moving three times as fast as the
// band and lifting as it goes.
class DonBG5 extends DonBG{
	constructor(background, index, half){
		super(background, index, half)
		this.overlayMove = BgAnim.get(this.manifest, "2")
		this.overlay1Width = (this.tex.info("overlay_1") || {w: 1}).w
		this.overlay2Width = (this.tex.info("overlay_2") || {w: 1}).w
	}
	
	update(ms){
		super.update(ms)
		this.overlayMove.update(ms)
	}
	
	drawTextures(ctx, fade, y, frame){
		this.drawBand(ctx, fade, y, frame)
		// Every other tile, so the front layer is sparser than the band.
		var front = this.tiles(this.overlay1Width * 2, this.move.attribute * 3)
		for(var i = 0; i < front.length; i++){
			this.tex.draw(ctx, "overlay_1", {
				frame: frame, fade: fade, x: front[i],
				y: y - this.move.attribute * 0.85
			})
		}
		var back = this.tiles(this.overlay2Width, this.move.attribute)
		for(var i = 0; i < back.length; i++){
			this.tex.draw(ctx, "overlay_2", {
				frame: frame, fade: fade, x: back[i],
				y: y + this.overlayMove.attribute
			})
		}
	}
}

/*
 * The five standard backgrounds. They share a base and almost nothing
 * else: two are a picture with a flickering light over it, one is a
 * stadium assembled from eleven pieces, one is a spring night with a
 * turtle and falling petals, and one is a row of paper lanterns.
 */
class BGNormal{
	constructor(background, index){
		this.background = background
		this.tex = background.tex("bg_normal/bg_" + index)
		this.manifest = background.manifest
		this.index = index
	}
	
	static create(background, index){
		var variants = [BGNormal01, BGNormal01, BGNormal2, BGNormal3, BGNormal4]
		var variant = variants[index] || BGNormal
		return new variant(background, index)
	}
	
	update(ms){}
	
	draw(ctx){
		this.tex.draw(ctx, "background")
	}
}

// Sets 0 and 1: lantern light, which the skin flickers between 0.5 and
// 0.4 opacity every 67ms. Not a strobe -- a slight unsteadiness.
class BGNormal01 extends BGNormal{
	constructor(background, index){
		super(background, index)
		this.flicker = BgAnim.get(this.manifest, "9")
	}
	
	update(ms){
		this.flicker.update(ms)
	}
	
	draw(ctx){
		this.tex.draw(ctx, "background")
		this.tex.draw(ctx, "overlay", {fade: this.flicker.attribute})
	}
}

// Set 2: a stadium. The background is an 8px gradient stretched right
// across, and everything that makes it a stadium sits on top of it.
class BGNormal2 extends BGNormal{
	constructor(background, index){
		super(background, index)
		this.flicker = BgAnim.get(this.manifest, "10")
	}
	
	update(ms){
		this.flicker.update(ms)
	}
	
	draw(ctx){
		var fade = this.flicker.attribute
		this.tex.draw(ctx, "background")
		this.tex.draw(ctx, "center")
		this.tex.draw(ctx, "overlay")
		this.tex.draw(ctx, "lamps", {index: 0})
		this.tex.draw(ctx, "lamps", {index: 1, mirror: "horizontal"})
		this.tex.draw(ctx, "light_orange", {index: 0, fade: fade})
		this.tex.draw(ctx, "light_orange", {index: 1, fade: fade})
		this.tex.draw(ctx, "light_red", {fade: fade})
		this.tex.draw(ctx, "light_green", {fade: fade})
		this.tex.draw(ctx, "light_orange", {index: 2, fade: fade})
		this.tex.draw(ctx, "light_yellow", {index: 0, fade: fade})
		this.tex.draw(ctx, "light_yellow", {index: 1, fade: fade})
		this.tex.draw(ctx, "side_l")
		this.tex.draw(ctx, "side_l_2")
		this.tex.draw(ctx, "side_r")
	}
}

// Set 3: petals fall through the lower half of the screen and are
// replaced as they land, and a turtle crosses over six and a half
// seconds. Petals never spawn in the middle of the screen, where the
// character stands.
class BGNormal3 extends BGNormal{
	constructor(background, index){
		super(background, index)
		this.flicker = BgAnim.get(this.manifest, "11")
		this.turtleMove = BgAnim.get(this.manifest, "12")
		this.turtleChange = BgAnim.get(this.manifest, "13")
		this.petals = []
		for(var i = 0; i < 5; i++){
			this.petals.push(this.newPetal())
		}
	}
	
	newPetal(){
		var random = this.background.random
		var spawn
		do{
			spawn = random.int(0, 1280)
		}while(spawn >= 260 && spawn <= 540)
		var duration = random.int(1400, 2000)
		var petal = {
			spawn: spawn,
			moveX: new BgMove(duration, {total_distance: random.int(-300, 300)}),
			moveY: new BgMove(duration, {total_distance: 360})
		}
		petal.moveX.start()
		petal.moveY.start()
		return petal
	}
	
	update(ms){
		this.flicker.update(ms)
		this.turtleMove.update(ms)
		this.turtleChange.update(ms)
		for(var i = this.petals.length - 1; i >= 0; i--){
			this.petals[i].moveX.update(ms)
			this.petals[i].moveY.update(ms)
			if(this.petals[i].moveY.isFinished){
				this.petals.splice(i, 1)
				this.petals.push(this.newPetal())
			}
		}
	}
	
	draw(ctx){
		this.tex.draw(ctx, "background")
		this.tex.draw(ctx, "chara")
		this.tex.draw(ctx, "turtle", {
			frame: this.turtleChange.attribute,
			x: this.turtleMove.attribute
		})
		this.tex.draw(ctx, "overlay")
		for(var i = 0; i < this.petals.length; i++){
			this.tex.draw(ctx, "petal", {
				x: this.petals[i].spawn + this.petals[i].moveX.attribute,
				y: 360 + this.petals[i].moveY.attribute,
				fade: 0.75
			})
		}
	}
}

// Set 4: ten paper lanterns, each drawn on a different frame so the row
// is not one shape repeated, with the light behind them flickering.
class BGNormal4 extends BGNormal{
	constructor(background, index){
		super(background, index)
		this.flicker = BgAnim.get(this.manifest, "14")
	}
	
	update(ms){
		this.flicker.update(ms)
	}
	
	draw(ctx){
		var fade = this.flicker.attribute
		this.tex.draw(ctx, "background")
		for(var i = 0; i < 10; i++){
			this.tex.draw(ctx, "paper_lamp", {frame: 9 - i, index: i})
		}
		for(var i = 0; i < 10; i++){
			this.tex.draw(ctx, "light_overlay", {index: i, fade: fade})
		}
		this.tex.draw(ctx, "overlay", {fade: 0.75})
		this.tex.draw(ctx, "lamp_overlay", {index: 0, fade: 0.75})
		this.tex.draw(ctx, "lamp_overlay", {index: 1, fade: 0.75})
		this.tex.draw(ctx, "lamp", {index: 0})
		this.tex.draw(ctx, "lamp", {index: 1})
	}
}

// Lua's modulo, which follows the sign of the divisor. Several of these
// animations count downwards, and the JavaScript one would hand back a
// negative angle.
function bgMod(value, by){
	return ((value % by) + by) % by
}

/*
 * Fever: what the background becomes once the gauge reaches clear.
 *
 * Four sets that are four different animations rather than one with a
 * variant. They share only the idea that arriving takes a moment, which
 * `transitioned` reports -- until it is true the standard background
 * keeps drawing underneath.
 */
class BGFever{
	constructor(background, index){
		this.background = background
		this.tex = background.tex("bg_fever/bg_fever_" + index)
		this.manifest = background.manifest
		this.index = index
		this.transitioned = false
	}
	
	static create(background, index){
		var variants = [BGFever0, BGFever1, BGFever2, BGFever3]
		var variant = variants[index] || BGFever
		return new variant(background, index)
	}
	
	start(){}
	update(ms){}
	draw(ctx){}
}

/*
 * Set 0. Twenty tiles expand out of the middle of the screen, one every
 * 66ms, while a corner, a footer, a mountain and an overlay each bounce
 * in a tenth of a second behind the one before.
 */
class BGFever0 extends BGFever{
	constructor(background, index){
		super(background, index)
		this.wait = null
		this.tiles = []
		this.isTransitioned = false
		
		// The skin declares one bounce; the four pieces are the same
		// bounce started at four different moments.
		this.cornerUp = new BgMove(133, {total_distance: 360, ease_out: "quadratic"})
		this.cornerDown = new BgMove(133, {total_distance: 160, ease_in: "quadratic", delay: 133})
		this.footerUp = new BgMove(133, {total_distance: 360, ease_out: "quadratic", delay: 100})
		this.footerDown = new BgMove(133, {total_distance: 160, ease_in: "quadratic", delay: 233})
		this.mountainUp = new BgMove(133, {total_distance: 360, ease_out: "quadratic", delay: 200})
		this.mountainDown = new BgMove(133, {total_distance: 160, ease_in: "quadratic", delay: 333})
		this.overlayUp = new BgMove(133, {total_distance: 360, ease_out: "quadratic", delay: 300})
		this.overlayDown = new BgMove(133, {total_distance: 160, ease_in: "quadratic", delay: 433})
		this.bounces = [
			this.cornerUp, this.cornerDown, this.footerUp, this.footerDown,
			this.mountainUp, this.mountainDown, this.overlayUp, this.overlayDown
		]
		
		this.waveSpin = BgAnim.get(this.manifest, "28")
		this.bgMove = BgAnim.get(this.manifest, "16")
		this.circle = {x: 100, y: 130, radius: 200}
	}
	
	wavePosition(){
		var angle = bgMod(this.waveSpin.attribute, 180) / 180 * 2 * Math.PI
		return [
			this.circle.x + Math.cos(angle) * this.circle.radius,
			this.circle.y + Math.sin(angle) * this.circle.radius
		]
	}
	
	start(){
		for(var i = 0; i < this.bounces.length; i++){
			this.bounces[i].start()
		}
	}
	
	update(ms){
		if(this.wait === null){
			this.wait = ms
		}
		if(this.tiles.length < 20 && ms >= this.wait + 66){
			var tile = new BgMove(166, {total_distance: 360})
			tile.start()
			this.tiles.push(tile)
			this.wait = ms
		}
		for(var i = 0; i < this.tiles.length; i++){
			this.tiles[i].update(ms)
		}
		for(var i = 0; i < this.bounces.length; i++){
			this.bounces[i].update(ms)
		}
		this.waveSpin.update(ms)
		
		var expanded = this.overlayDown.isFinished && this.tiles.length === 20
		if(expanded && !this.isTransitioned){
			this.bgMove.restart()
		}
		this.isTransitioned = expanded
		if(this.isTransitioned){
			this.bgMove.update(ms)
		}
	}
	
	draw(ctx){
		var width = (this.tex.info("background") || {w: 1}).w
		for(var i = 0; i < this.tiles.length; i++){
			var expansion = this.tiles[i].attribute
			this.tex.draw(ctx, "background", {
				frame: i % 10,
				x: i * width - this.bgMove.attribute,
				y: 360 + (180 - expansion / 2),
				y2: -360 + expansion
			})
		}
		
		this.tex.draw(ctx, "mountain", {y: -this.mountainUp.attribute + this.mountainDown.attribute})
		var wave = this.wavePosition()
		var info = this.tex.info("wave") || {w: 0, h: 0}
		this.tex.draw(ctx, "wave", {
			x: wave[0], y: wave[1], origin: [info.w / 2, info.h / 2]
		})
		this.tex.draw(ctx, "footer", {y: -this.footerUp.attribute + this.footerDown.attribute})
		this.tex.draw(ctx, "corner", {y: -this.cornerUp.attribute + this.cornerDown.attribute})
		this.tex.draw(ctx, "overlay", {y: this.overlayUp.attribute - this.overlayDown.attribute})
	}
}

// Set 1: a ship swoops in from the left and settles, two birds part
// around it, and the whole thing fades up over 416ms.
class BGFever1 extends BGFever{
	constructor(background, index){
		super(background, index)
		this.fadeIn = BgAnim.get(this.manifest, "19")
		this.bgChange = BgAnim.get(this.manifest, "20")
		this.shipRotation = BgAnim.get(this.manifest, "21")
		this.moveIn = BgAnim.get(this.manifest, "22")
		this.moveOut = BgAnim.get(this.manifest, "23")
		var info = this.tex.info("ship") || {w: 0, h: 0}
		this.shipOrigin = [info.w / 2, info.h / 2]
	}
	
	start(){
		this.fadeIn.start()
		this.moveIn.start()
		this.moveOut.start()
	}
	
	update(ms){
		this.fadeIn.update(ms)
		this.bgChange.update(ms)
		this.shipRotation.update(ms)
		this.moveIn.update(ms)
		this.moveOut.update(ms)
		this.transitioned = this.moveOut.isFinished
	}
	
	draw(ctx){
		var move = this.moveIn.attribute - this.moveOut.attribute
		var fade = this.fadeIn.attribute
		var spin = this.shipRotation.attribute
		
		this.tex.draw(ctx, "background", {frame: this.bgChange.attribute, fade: fade})
		this.tex.draw(ctx, "footer_3", {y: move, fade: fade})
		this.tex.draw(ctx, "footer_1", {y: move, fade: fade})
		this.tex.draw(ctx, "footer_2", {y: move, fade: fade})
		this.tex.draw(ctx, "bird", {index: 0, x: move, mirror: "horizontal", y: spin * 180})
		this.tex.draw(ctx, "bird", {index: 1, x: -move, y: spin * 180})
		this.tex.draw(ctx, "ship", {
			x: this.shipOrigin[0],
			y: this.shipOrigin[1] + move,
			origin: this.shipOrigin,
			rotation: spin * 100,
			center: true
		})
	}
}

// Set 2: sixteen fish orbit a turning circle, each facing the way it is
// going, while the background slides in behind them.
class BGFever2 extends BGFever{
	constructor(background, index){
		super(background, index)
		this.fadeIn = BgAnim.get(this.manifest, "19")
		this.moveIn = BgAnim.get(this.manifest, "24")
		this.footerUp = BgAnim.get(this.manifest, "26")
		this.birdChange = BgAnim.get(this.manifest, "20")
		this.overlayChange = BgAnim.get(this.manifest, "25")
		this.circleRotate = BgAnim.get(this.manifest, "27")
		this.fishSpin = BgAnim.get(this.manifest, "28")
		this.circle = {x: 500, y: 300, radius: 300}
		this.phases = []
		for(var i = 0; i < 8; i++){
			this.phases.push(i * (2 * Math.PI) / 8)
		}
		this.waveOrigin = this.originOf("wave")
		this.fishOrigin = this.originOf("fish")
		this.circleOrigin = this.originOf("circle")
	}
	
	originOf(key){
		var info = this.tex.info(key) || {w: 0, h: 0}
		return [info.w / 2, info.h / 2]
	}
	
	mainPosition(spin, multiplier){
		var angle = bgMod(spin * multiplier, 360) / 360 * 2 * Math.PI
		return [
			this.circle.x + Math.cos(angle) * this.circle.radius,
			this.circle.y + Math.sin(angle) * this.circle.radius
		]
	}
	
	smallPosition(spin, multiplier){
		var angle = bgMod(spin * multiplier, 360) / 360 * 2 * Math.PI
		return [this.circle.x + Math.cos(angle) * 20, this.circle.y + Math.sin(angle) * 20]
	}
	
	fishPosition(spin, phase){
		var angle = bgMod(spin + phase * 180 / Math.PI, 360) / 360 * 2 * Math.PI
		return [
			this.circle.x + Math.cos(angle) * this.circle.radius,
			this.circle.y + Math.sin(angle) * this.circle.radius,
			(angle + Math.PI / 2) * 180 / Math.PI
		]
	}
	
	start(){
		this.fadeIn.start()
		this.moveIn.start()
		this.footerUp.start()
	}
	
	update(ms){
		this.fadeIn.update(ms)
		this.moveIn.update(ms)
		this.birdChange.update(ms)
		this.overlayChange.update(ms)
		this.footerUp.update(ms)
		this.circleRotate.update(ms)
		this.fishSpin.update(ms)
		this.transitioned = this.moveIn.isFinished
	}
	
	draw(ctx){
		var fade = this.fadeIn.attribute
		var spin = this.fishSpin.attribute
		
		this.tex.draw(ctx, "background", {x: -this.moveIn.attribute})
		this.tex.draw(ctx, "overlay", {frame: this.overlayChange.attribute, fade: fade})
		this.tex.draw(ctx, "circle", {
			x: this.circleOrigin[0], y: this.circleOrigin[1],
			fade: fade, origin: this.circleOrigin, rotation: this.circleRotate.attribute
		})
		
		var wave = this.mainPosition(spin, 2)
		this.tex.draw(ctx, "wave", {x: wave[0], y: wave[1], fade: fade, origin: this.waveOrigin})
		
		for(var index = 0; index < 2; index++){
			for(var i = 0; i < this.phases.length; i++){
				var fish = this.fishPosition(spin, this.phases[i])
				this.tex.draw(ctx, "fish", {
					x: fish[0], y: fish[1], fade: fade,
					origin: this.fishOrigin, rotation: fish[2], index: index
				})
			}
		}
		
		var foam = this.smallPosition(spin, 3)
		for(var i = 0; i < 3; i++){
			this.tex.draw(ctx, "footer_2", {
				x: foam[0] + i * 600, y: foam[1], fade: fade, origin: this.waveOrigin
			})
		}
		for(var i = 0; i < 3; i++){
			this.tex.draw(ctx, "footer_1", {x: i * 450, y: -this.footerUp.attribute})
		}
		this.tex.draw(ctx, "bird", {frame: this.birdChange.attribute, index: 0, x: -this.moveIn.attribute})
		this.tex.draw(ctx, "bird", {frame: this.birdChange.attribute, index: 1, x: -this.moveIn.attribute})
	}
}

// Set 3: a tiled background drops half a second and lifts back 40, and
// once it has settled it scrolls both ways for the rest of the song.
class BGFever3 extends BGFever{
	constructor(background, index){
		super(background, index)
		this.verticalMove = BgAnim.get(this.manifest, "15")
		this.horizontalMove = BgAnim.get(this.manifest, "16")
		this.moveDown = BgAnim.get(this.manifest, "17")
		this.moveUp = BgAnim.get(this.manifest, "18")
	}
	
	start(){
		this.moveDown.start()
		this.moveUp.start()
	}
	
	update(ms){
		this.moveDown.update(ms)
		this.moveUp.update(ms)
		if(this.moveUp.isFinished && !this.transitioned){
			this.transitioned = true
			this.verticalMove.restart()
			this.horizontalMove.restart()
		}
		if(this.transitioned){
			this.verticalMove.update(ms)
			this.horizontalMove.update(ms)
		}
	}
	
	draw(ctx){
		var width = (this.tex.info("background") || {w: 1}).w
		var y = this.moveDown.attribute - this.moveUp.attribute
		for(var i = 0; i <= width * 12; i += width){
			this.tex.draw(ctx, "background", {x: i, y: y})
		}
		this.tex.draw(ctx, "overlay_1", {y: -this.verticalMove.attribute - y})
		var overlayWidth = (this.tex.info("overlay_2") || {w: 0}).w
		this.tex.draw(ctx, "overlay_2", {x: -this.horizontalMove.attribute, y: y})
		this.tex.draw(ctx, "overlay_2", {x: overlayWidth - this.horizontalMove.attribute, y: y})
	}
}

/*
 * The rainbow overlay: the two glows at the bottom corners that appear
 * only once the gauge is full, bouncing 50px on every half beat.
 */
class Fever{
	constructor(background, index, bpm){
		this.tex = background.tex("fever/fever_" + index)
		this.index = index
		this.setBounce(bpm)
	}
	
	setBounce(bpm){
		var halfBeat = (60000 / bpm) / 2
		this.bounceUp = new BgMove(halfBeat, {total_distance: 50, ease_out: "quadratic"})
		this.bounceDown = new BgMove(halfBeat, {total_distance: 50, ease_in: "quadratic", delay: halfBeat})
	}
	
	start(){
		this.bounceUp.start()
		this.bounceDown.start()
	}
	
	update(ms, bpm){
		this.bounceUp.update(ms)
		this.bounceDown.update(ms)
		if(this.bounceDown.isFinished){
			this.setBounce(bpm)
			this.start()
		}
	}
	
	draw(ctx, span){
		var y = this.bounceDown.attribute - this.bounceUp.attribute
		if(this.tex.has("overlay")){
			this.tex.draw(ctx, "overlay", {y: y})
		}else{
			// One in each bottom corner, so they follow the window's
			// corners rather than the frame's.
			this.tex.draw(ctx, "overlay_l", {x: span.left, y: y})
			this.tex.draw(ctx, "overlay_r", {x: span.right - 1280, y: y})
		}
	}
}

/*
 * A dancer.
 *
 * The entrance is a beat long: a wait of half a second, then up 350 over
 * half a beat easing out and down 140 over the next easing in, with a
 * start animation playing over the whole of it. After that it loops --
 * and the loop is not frames 0 to n. The skin writes out the order, and
 * it goes forward, back and around; the manifest carries it and BgTex
 * applies it, so the frame numbers here are positions in the dance.
 */
class BgDancer{
	constructor(group, index, bpm){
		this.tex = group.tex
		this.group = group
		this.index = index
		this.bpm = bpm
		this.isStarted = false
		this.keyframeCount = this.tex.frameCount(index + "_loop")
		this.buildLoop(bpm)
	}
	
	buildLoop(bpm){
		var duration = (60000 / bpm) / 2
		this.textureChange = BgTextureChange.even(duration * this.keyframeCount, this.keyframeCount, {loop: true})
		this.textureChange.start()
	}
	
	start(){
		this.isStarted = true
		var duration = 60000 / this.bpm
		this.bounceUp = new BgMove(duration / 2, {
			start_position: -200, total_distance: 350, ease_out: "quadratic", delay: 500
		})
		this.bounceDown = new BgMove(duration / 2, {
			total_distance: 140, ease_in: "quadratic", delay: duration / 2 + 500
		})
		this.startChange = BgTextureChange.even(duration, this.tex.frameCount(this.index + "_start"), {delay: 500})
		this.startChange.start()
		this.bounceUp.start()
		this.bounceDown.start()
	}
	
	update(ms, bpm){
		this.textureChange.update(ms)
		if(this.isStarted){
			this.startChange.update(ms)
			this.bounceUp.update(ms)
			this.bounceDown.update(ms)
		}
		if(bpm && bpm !== this.bpm){
			this.bpm = bpm
			this.buildLoop(bpm)
		}
	}
	
	entrance(){
		return -this.bounceUp.attribute + this.bounceDown.attribute
	}
	
	draw(ctx, x){
		if(!this.isStarted){
			return
		}
		if(!this.startChange.isFinished){
			this.tex.draw(ctx, this.index + "_start", {
				frame: this.startChange.attribute, x: x, y: this.entrance()
			})
		}else{
			this.tex.draw(ctx, this.index + "_loop", {
				frame: this.textureChange.attribute, x: x
			})
		}
	}
}

// Set 0's fifth dancer carries something that bounces on its own, drawn
// from three frames past the end of the dance.
class BgDancer04 extends BgDancer{
	constructor(group, index, bpm){
		super(group, index, bpm)
		this.keyframeCount = 54
		this.buildLoop(bpm)
		var duration = (60000 / bpm) / 2
		this.objectUp = new BgMove(duration, {total_distance: 20, ease_out: "quadratic", delay: duration * 2})
		this.objectDown = new BgMove(duration, {total_distance: 20, ease_in: "quadratic", delay: duration * 3})
		this.objectUp.start()
		this.objectDown.start()
	}
	
	update(ms, bpm){
		super.update(ms, bpm)
		this.objectUp.update(ms)
		this.objectDown.update(ms)
		if(this.objectDown.isFinished){
			this.objectUp.restart()
			this.objectDown.restart()
		}
	}
	
	draw(ctx, x){
		if(!this.isStarted){
			return
		}
		if(!this.startChange.isFinished){
			this.tex.draw(ctx, "4_start", {frame: 7, x: x, y: -50 + this.entrance()})
			this.tex.draw(ctx, "4_start", {frame: this.startChange.attribute, x: x, y: this.entrance()})
		}else{
			var frame = this.textureChange.attribute
			var y = -this.objectUp.attribute + this.objectDown.attribute
			if(frame >= 0 && frame <= 3){
				this.tex.draw(ctx, "4_loop", {frame: 54, x: x, y: y})
			}else if(frame >= 5 && frame <= 8){
				this.tex.draw(ctx, "4_loop", {frame: 56, x: x, y: y})
			}else if(frame === 4){
				this.tex.draw(ctx, "4_loop", {frame: 55, x: x, y: y})
			}
			this.tex.draw(ctx, "4_loop", {frame: frame, x: x})
		}
	}
}

// Some sets puff into existence rather than walking on.
class BgDancerPoof extends BgDancer{
	constructor(group, index, bpm, perIndex){
		super(group, index, bpm)
		this.poofKey = perIndex ? index + "_poof" : "poof"
		this.perIndex = perIndex
		var duration = 60000 / bpm
		this.poofChange = BgTextureChange.even(duration, 7, {delay: 250})
		this.poofChange.start()
	}
	
	update(ms, bpm){
		super.update(ms, bpm)
		this.poofChange.update(ms)
	}
	
	draw(ctx, x){
		super.draw(ctx, x)
		if(this.isStarted && !this.poofChange.isFinished){
			this.tex.draw(ctx, this.poofKey, {x: x, frame: this.poofChange.attribute})
		}
	}
}

/*
 * The dancers as a group, and the part of this that changes how the
 * screen feels.
 *
 * There is one dancer at the start of a song, not five. The rest are
 * earned: the gauge is divided into five and one arrives at each mark,
 * the fifth only on clear, and dropping back below a mark sends one
 * away again. They stand in five fixed slots filled from the middle
 * outwards, so the group grows symmetrically and nobody shuffles
 * sideways when another arrives.
 */
class DancerGroup{
	constructor(background, index, bpm, maxDancers, makeDancer){
		this.tex = background.tex("dancer/dancer_" + index)
		this.index = index
		this.maxDancers = maxDancers
		this.activeCount = 0
		// centre, left, right, far-left, far-right
		this.spawnPositions = [2, 1, 3, 0, 4]
		this.activeDancers = [null, null, null, null, null]
		this.needsInitialDancer = true
		
		var variants = this.variantCount()
		this.dancers = []
		for(var i = 0; i < maxDancers; i++){
			this.dancers.push(makeDancer(this, i % variants, i, bpm))
		}
		// Which dancer stands where is shuffled, so the same set does
		// not put the same one in the middle every time.
		for(var i = this.dancers.length - 1; i > 0; i--){
			var j = background.random.int(0, i)
			var swap = this.dancers[i]
			this.dancers[i] = this.dancers[j]
			this.dancers[j] = swap
		}
	}
	
	static create(background, index, bpm, maxDancers){
		// Sets 0-2 give their fifth dancer a bouncing object; 7 and 8
		// share one puff of smoke between them, 12, 13 and 16 have one
		// each. The rest walk on.
		var makeDancer = (group, variant, slot, tempo) => new BgDancer(group, variant, tempo)
		if(index <= 2){
			makeDancer = (group, variant, slot, tempo) => slot === 4
				? new BgDancer04(group, 4, tempo)
				: new BgDancer(group, slot, tempo)
		}else if(index === 7 || index === 8){
			makeDancer = (group, variant, slot, tempo) => new BgDancerPoof(group, variant, tempo, false)
		}else if(index === 12 || index === 13 || index === 16){
			makeDancer = (group, variant, slot, tempo) => new BgDancerPoof(group, variant, tempo, true)
		}
		return new DancerGroup(background, index, bpm, maxDancers, makeDancer)
	}
	
	// A set does not always have five different dancers -- some have
	// three, and the five slots reuse them in turn.
	variantCount(){
		var seen = {}
		var prefix = this.tex.prefix + "_"
		for(var name in this.tex.manifest.assets){
			if(name.startsWith(prefix) && name.endsWith("_loop")){
				var variant = name.slice(prefix.length, -"_loop".length)
				if(/^\d+$/.test(variant)){
					seen[variant] = true
				}
			}
		}
		return Math.max(1, Object.keys(seen).length)
	}
	
	addDancer(){
		if(this.activeCount < this.dancers.length && this.activeCount < this.spawnPositions.length){
			var position = this.spawnPositions[this.activeCount]
			var dancer = this.dancers[this.activeCount]
			this.activeCount++
			this.activeDancers[position] = dancer
			dancer.start()
		}
	}
	
	removeDancer(){
		if(this.activeCount > 1){
			this.activeCount--
			this.activeDancers[this.spawnPositions[this.activeCount]] = null
		}
	}
	
	update(ms, bpm){
		if(this.needsInitialDancer){
			this.needsInitialDancer = false
			this.addDancer()
		}
		for(var i = 0; i < this.dancers.length; i++){
			this.dancers[i].update(ms, bpm)
		}
	}
	
	draw(ctx, span){
		var first = null
		for(var i = 0; i < this.maxDancers; i++){
			if(this.activeDancers[i]){
				first = this.activeDancers[i]
				break
			}
		}
		if(!first){
			return
		}
		// The slots are laid out for a full set whether or not it is
		// full, so a dancer stands in the same place all song, and they
		// are spread across the window rather than across the frame.
		var info = this.tex.info(first.index + "_loop")
		var width = info ? info.w : 0
		var spacing = (span.width - this.maxDancers * width) / (this.maxDancers + 1)
		for(var i = 0; i < this.maxDancers; i++){
			if(this.activeDancers[i]){
				this.activeDancers[i].draw(ctx,
					Math.floor(span.left + spacing + i * (width + spacing)))
			}
		}
	}
}

// The strip along the bottom of the screen. Three of them; a song gets
// one and it does not move.
class BgFooter{
	constructor(background, index){
		this.tex = background.tex("footer")
		this.index = index
	}
	
	// A repeating pattern, so a window wider than the frame gets more of
	// it rather than a black strip at each end.
	draw(ctx, span){
		var info = this.tex.info(String(this.index))
		var width = info ? info.w : 1280
		for(var x = Math.floor(span.left / width) * width; x < span.right; x += width){
			this.tex.draw(ctx, String(this.index), {x: x})
		}
	}
}

/*
 * The character that runs across the background on a drumroll or a
 * balloon. One is thrown for every drumroll hit and dropped once it
 * leaves the screen.
 */
class BgRenda{
	constructor(controller, index){
		this.tex = controller.tex
		this.index = index
		this.key = "renda_" + index
		this.random = controller.random
		var span = controller.span()
		this.horiMove = new BgMove(1500, {
			start_position: span.left, total_distance: span.width
		})
		this.horiMove.start()
	}
	
	static create(controller, index){
		var variants = [BgRenda0, BgRenda1, BgRenda2]
		var variant = variants[index] || BgRenda0
		return new variant(controller, index)
	}
	
	update(ms){
		this.horiMove.update(ms)
	}
}

// Rises as it crosses.
class BgRenda0 extends BgRenda{
	constructor(controller, index){
		super(controller, index)
		this.vertMove = new BgMove(1500, {total_distance: 800})
		this.vertMove.start()
		this.frame = this.random.int(0, this.tex.frameCount(this.key) - 1)
		this.x = this.random.int(0, 500)
		this.y = this.random.int(0, 20)
	}
	
	update(ms){
		super.update(ms)
		this.vertMove.update(ms)
	}
	
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			frame: this.frame,
			x: this.horiMove.attribute + this.x,
			y: -this.vertMove.attribute + this.y
		})
	}
}

// Spins as it crosses.
class BgRenda1 extends BgRenda{
	constructor(controller, index){
		super(controller, index)
		this.frame = this.random.int(0, 5)
		this.y = this.random.int(0, 200)
		this.rotate = new BgMove(800, {total_distance: 360, loop: true})
		this.rotate.start()
		this.origin = [64, 64]
	}
	
	update(ms){
		super.update(ms)
		this.rotate.update(ms)
	}
	
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			frame: this.frame,
			x: this.horiMove.attribute + this.origin[0],
			y: this.y + this.origin[1],
			origin: this.origin,
			rotation: this.rotate.attribute
		})
	}
}

// Just crosses.
class BgRenda2 extends BgRenda{
	constructor(controller, index){
		super(controller, index)
		this.vertMove = new BgMove(1500, {total_distance: 800})
		this.vertMove.start()
		this.x = this.random.int(0, 500)
		this.y = this.random.int(0, 20)
	}
	
	update(ms){
		super.update(ms)
		this.vertMove.update(ms)
	}
	
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			x: this.horiMove.attribute + this.x,
			y: -this.vertMove.attribute + this.y
		})
	}
}

class RendaController{
	constructor(background, index){
		this.background = background
		this.tex = background.tex("renda")
		this.random = background.random
		this.index = index
		this.rendas = []
	}
	
	span(){
		return this.background.span
	}
	
	add(){
		this.rendas.push(BgRenda.create(this, this.index))
	}
	
	update(ms){
		for(var i = this.rendas.length - 1; i >= 0; i--){
			this.rendas[i].update(ms)
			if(this.rendas[i].horiMove.isFinished){
				this.rendas.splice(i, 1)
			}
		}
	}
	
	draw(ctx){
		for(var i = 0; i < this.rendas.length; i++){
			this.rendas[i].draw(ctx)
		}
	}
}

/*
 * The small character that crosses the background on a hit -- a
 * different, sadder one on a miss, which fades in rather than simply
 * appearing. It takes five beats to cross and is dropped when it gets
 * there.
 */
class BgChibi{
	constructor(controller, index, bpm){
		this.tex = controller.tex
		this.controller = controller
		this.index = index
		this.bpm = bpm
		this.key = String(controller.random.pick(controller.characters))
		this.build(bpm)
	}
	
	static create(controller, index, bpm, bad){
		if(bad){
			return new BgChibiBad(controller, index, bpm)
		}
		if(index === 0){
			return new BgChibi0(controller, index, bpm)
		}
		if(index === 2){
			return new BgChibi2(controller, index, bpm)
		}
		if(index === 4 || index === 5 || index === 8){
			return new BgChibiFlat(controller, index, bpm)
		}
		if(index === 13){
			return new BgChibi13(controller, index, bpm)
		}
		return new BgChibi(controller, index, bpm)
	}
	
	build(bpm){
		var span = this.controller.background.span
		this.horiMove = new BgMove(60000 / bpm * 5, {
			start_position: span.left, total_distance: span.width
		})
		this.horiMove.start()
		this.vertMove = new BgMove(60000 / bpm / 2, {total_distance: 50, reverse_delay: 0, loop: true})
		this.vertMove.start()
		this.rebuildFrames(bpm)
	}
	
	rebuildFrames(bpm){
		var duration = (60000 / bpm) / 2
		this.textureChange = BgTextureChange.even(duration, this.tex.frameCount(this.key), {loop: true})
		this.textureChange.start()
	}
	
	update(ms, bpm){
		this.horiMove.update(ms)
		this.vertMove.update(ms)
		this.textureChange.update(ms)
		if(bpm && bpm !== this.bpm){
			this.bpm = bpm
			this.rebuildFrames(bpm)
			this.horiMove.duration = 60000 / bpm * 5
			this.vertMove.duration = 60000 / bpm / 2
		}
	}
	
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			frame: this.textureChange.attribute,
			x: this.horiMove.attribute,
			y: -this.vertMove.attribute
		})
	}
}

// Set 0 bobs the other way.
class BgChibi0 extends BgChibi{
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			frame: this.textureChange.attribute,
			x: this.horiMove.attribute,
			y: this.vertMove.attribute
		})
	}
}

// Set 2 rolls rather than bobs.
class BgChibi2 extends BgChibi{
	constructor(controller, index, bpm){
		super(controller, index, bpm)
		this.rotate = new BgMove(60000 / bpm, {total_distance: 360})
		this.rotate.start()
	}
	
	update(ms, bpm){
		super.update(ms, bpm)
		this.rotate.update(ms)
		if(this.rotate.isFinished){
			this.rotate.restart()
		}
		if(bpm && bpm !== this.bpm){
			this.rotate.duration = 60000 / bpm
		}
	}
	
	draw(ctx){
		var info = this.tex.info(this.key)
		if(!info){
			return
		}
		var origin = [info.w / 2, info.h / 2]
		this.tex.draw(ctx, this.key, {
			frame: this.textureChange.attribute,
			x: this.horiMove.attribute + origin[0],
			y: origin[1],
			origin: origin,
			rotation: this.rotate.attribute
		})
	}
}

// Sets 4, 5 and 8 walk level.
class BgChibiFlat extends BgChibi{
	draw(ctx){
		this.tex.draw(ctx, this.key, {
			frame: this.textureChange.attribute,
			x: this.horiMove.attribute,
			y: 0
		})
	}
}

// Set 13 breathes: it shrinks to three quarters on the off beat, and
// has a tail drawn behind it.
class BgChibi13 extends BgChibi{
	constructor(controller, index, bpm){
		super(controller, index, bpm)
		this.buildScale(bpm)
		this.frame = 0
	}
	
	buildScale(bpm){
		var duration = 60000 / bpm
		this.scale = new BgFade(duration, {
			initial_opacity: 1, final_opacity: 0.75,
			delay: duration, reverse_delay: duration, loop: true
		})
		this.scale.start()
	}
	
	update(ms, bpm){
		super.update(ms, bpm)
		this.scale.update(ms)
		if(bpm && bpm !== this.bpm){
			this.buildScale(bpm)
		}
		this.frame = this.scale.attribute === 0.75 ? 1 : 0
	}
	
	draw(ctx){
		var y = -this.vertMove.attribute
		this.tex.draw(ctx, "tail", {frame: this.frame, x: this.horiMove.attribute, y: y})
		if(this.scale.attribute === 0.75){
			this.tex.draw(ctx, this.key, {frame: this.frame, x: this.horiMove.attribute, y: y})
		}else{
			this.tex.draw(ctx, this.key, {
				frame: this.frame, scale: this.scale.attribute, center: true,
				x: this.horiMove.attribute, y: y
			})
		}
	}
}

// The one that appears on a miss. It comes from its own folder, so
// every set has the same sad character, and it fades in.
class BgChibiBad extends BgChibi{
	constructor(controller, index, bpm){
		super(controller, index, bpm)
		this.tex = controller.badTex
		this.key = "0"
		this.buildBad(bpm)
	}
	
	buildBad(bpm){
		var duration = (60000 / bpm) / 2
		var span = this.controller.background.span
		this.horiMove = new BgMove(duration * 10, {
			start_position: span.left, total_distance: span.width
		})
		this.horiMove.start()
		this.vertMove = new BgMove(duration, {total_distance: 50, reverse_delay: 0, loop: true})
		this.vertMove.start()
		this.fadeIn = new BgFade(duration, {initial_opacity: 0, final_opacity: 1})
		this.fadeIn.start()
		this.startChange = new BgTextureChange(duration, [
			[0, duration / 3, 0], [duration / 3, duration / 3 * 2, 1], [duration / 3 * 2, duration, 2]
		], {})
		this.startChange.start()
		this.textureChange = new BgTextureChange(duration * 2, [
			[0, duration, 3], [duration, duration * 2, 4]
		], {loop: true})
		this.textureChange.start()
	}
	
	update(ms, bpm){
		this.horiMove.update(ms)
		this.vertMove.update(ms)
		this.fadeIn.update(ms)
		this.startChange.update(ms)
		this.textureChange.update(ms)
		if(bpm && bpm !== this.bpm){
			this.bpm = bpm
			this.buildBad(bpm)
		}
	}
	
	draw(ctx){
		var y = this.vertMove.attribute
		if(!this.startChange.isFinished){
			this.tex.draw(ctx, "0", {
				frame: this.startChange.attribute, x: this.horiMove.attribute,
				y: y, fade: this.fadeIn.attribute
			})
		}else{
			this.tex.draw(ctx, "0", {
				frame: this.textureChange.attribute, x: this.horiMove.attribute, y: y
			})
		}
	}
}

class ChibiController{
	constructor(background, index, bpm){
		this.background = background
		this.tex = background.tex("chibi/chibi_" + index)
		this.badTex = background.tex("chibi/chibi_bad")
		this.random = background.random
		this.index = index
		this.bpm = bpm
		this.chibis = []
		this.characters = this.charactersOf()
	}
	
	// Which characters a set holds. Their keys are numbers; anything
	// else in the folder -- set 13's tail -- is not one of them.
	charactersOf(){
		var found = []
		var prefix = this.tex.prefix + "_"
		for(var name in this.tex.manifest.assets){
			if(name.startsWith(prefix)){
				var key = name.slice(prefix.length)
				if(/^\d+$/.test(key)){
					found.push(key)
				}
			}
		}
		return found.length ? found : ["0"]
	}
	
	add(bad){
		this.chibis.push(BgChibi.create(this, this.index, this.bpm, bad))
	}
	
	update(ms, bpm){
		if(bpm){
			this.bpm = bpm
		}
		for(var i = this.chibis.length - 1; i >= 0; i--){
			this.chibis[i].update(ms, this.bpm)
			if(this.chibis[i].horiMove.isFinished){
				this.chibis.splice(i, 1)
			}
		}
	}
	
	draw(ctx){
		for(var i = 0; i < this.chibis.length; i++){
			this.chibis[i].draw(ctx)
		}
	}
}

/*
 * A repeatable random.
 *
 * YataiDON picks its sets, its dancers' places and every petal with the
 * system random. Here it has to be the same twice: two players in a
 * session must see the same background, and the loader has to know which
 * art the song will want before any of this exists.
 */
class BgRandom{
	constructor(seed){
		this.state = (seed >>> 0) || 1
	}
	
	next(){
		this.state = (Math.imul(this.state, 1103515245) + 12345) >>> 0
		return this.state / 4294967296
	}
	
	int(min, max){
		return min + Math.floor(this.next() * (max - min + 1))
	}
	
	pick(list){
		return list[this.int(0, list.length - 1)]
	}
}

/*
 * What a song gets, and everything that follows from it.
 *
 * Taken from the song rather than at random, so a song looks the same
 * every time it is played and two players in a session see the same
 * thing. Shared with the loader, which has to know what to fetch before
 * any of this exists -- if the two disagreed, the song would load one
 * background and draw another.
 */
class GameBackground{
	constructor(...args){
		this.init(...args)
	}
	
	init(view){
		this.view = view
		this.manifest = assets.backgrounds
		this.ready = false
		if(!this.manifest || !this.manifest.assets){
			return
		}
		this.song = view.controller.selectedSong
		this.choice = GameBackground.choose(this.song, this.manifest)
		this.built = false
		this.isClear = false
		this.isRainbow = false
		this.lastMilestone = 1
		this.minimal = GameBackground.minimal()
		// The window is usually wider than the 1280 frame the art is
		// drawn for. Replaced with the real one on the first frame; a
		// default is here because a character can be thrown onto the
		// screen before anything has been drawn.
		this.span = {left: 0, right: 1280, width: 1280}
		this.ready = true
	}
	
	/*
	 * The still background: the scene, the band above the lanes and the
	 * footer, with nothing moving in front of them. For players who find
	 * dancers and characters behind the notes distracting.
	 */
	static minimal(){
		return typeof settings !== "undefined" && !!settings.getItem("minimalBackground")
	}
	
	tex(folder){
		return new BgTex(this.manifest, folder)
	}
	
	bpm(){
		return 60000 / (this.view.beatInterval || 512)
	}
	
	/*
	 * Built on the first frame rather than in the constructor: the
	 * animations stamp themselves with the clock as they are made, and
	 * until the song is running there is no clock to stamp.
	 */
	build(){
		var bpm = this.bpm()
		this.random = new BgRandom(GameBackground.seed(this.song))
		this.donbg = DonBG.create(this, this.choice.donSet, this.view.player === 2 ? 2 : 1)
		this.bgNormal = BGNormal.create(this, this.choice.bgSet)
		this.footer = new BgFooter(this, this.choice.footer)
		if(!this.minimal){
			this.bgFever = BGFever.create(this, this.choice.feverSet)
			this.feverFx = new Fever(this, this.choice.feverFxSet, bpm)
			this.dancers = DancerGroup.create(this, this.choice.dancerSet, bpm, 5)
			this.renda = new RendaController(this, this.choice.rendaSet)
			this.chibi = new ChibiController(this, this.choice.chibiSet, bpm)
		}
		this.built = true
	}
	
	static choose(song, manifest){
		var seed = GameBackground.seed(song)
		var pick = (list, offset) => (list && list.length) ? list[(seed + offset) % list.length] : 0
		return {
			donSet: pick(manifest.donSets, 0),
			bgSet: pick(manifest.bgSets, 1),
			feverSet: pick(manifest.feverSets, 2),
			feverFxSet: pick(manifest.feverSets, 3),
			dancerSet: pick(manifest.dancerSets, 4),
			footer: pick(manifest.footers, 5),
			rendaSet: pick(manifest.rendaSets, 6),
			chibiSet: pick(manifest.chibiSets, 7)
		}
	}
	
	static seed(song){
		var text = (song && (song.hash || song.title)) || ""
		var seed = 0
		for(var i = 0; i < text.length; i++){
			seed = (seed * 31 + text.charCodeAt(i)) % 100003
		}
		return seed
	}
	
	/*
	 * The folders one song needs. All of them together are 28MB, which
	 * is more than the game used to load before the title screen; a song
	 * needs a tenth of it, and loads that while its loading screen is up
	 * rather than while it is being played.
	 */
	static assetsFor(song, manifest){
		if(!manifest || !manifest.assets){
			return []
		}
		var choice = GameBackground.choose(song, manifest)
		var folders = [
			"donbg/" + choice.donSet + "_1",
			"donbg/" + choice.donSet + "_2",
			"bg_normal/bg_" + choice.bgSet,
			"footer"
		]
		// A still background draws none of the rest, so none of it is
		// worth fetching either.
		if(!GameBackground.minimal()){
			folders.push(
				"bg_fever/bg_fever_" + choice.feverSet,
				"fever/fever_" + choice.feverFxSet,
				"dancer/dancer_" + choice.dancerSet,
				"chibi/chibi_" + choice.chibiSet,
				"chibi/chibi_bad",
				"renda"
			)
		}
		var prefixes = folders.map(folder => "yatai_" + folder.replace(/\//g, "_") + "_")
		var wanted = []
		for(var name in manifest.assets){
			for(var i = 0; i < prefixes.length; i++){
				if(name.startsWith(prefixes[i])){
					wanted.push(name)
					break
				}
			}
		}
		return wanted
	}
	
	update(ms, gauge){
		if(!this.ready){
			return
		}
		BgAnim.now = ms
		this.ms = ms
		if(!this.built){
			this.build()
		}
		if(this.minimal){
			// Nothing is updated, so nothing advances past its first
			// frame: the scene, the band and the footer, held still.
			return
		}
		var bpm = this.bpm()
		this.donbg.update(ms)
		this.bgNormal.update(ms)
		this.bgFever.update(ms)
		this.feverFx.update(ms, bpm)
		this.dancers.update(ms, bpm)
		this.renda.update(ms)
		this.chibi.update(ms, bpm)
		this.handleGauge(gauge)
	}
	
	/*
	 * The gauge is what the background reacts to, and it does three
	 * things with it: light up the band above the lanes, bring on the
	 * fever scene, and decide how many dancers there are.
	 */
	handleGauge(gauge){
		gauge = gauge || {}
		var isClear = !!gauge.clear
		var isRainbow = !!gauge.rainbow
		this.donbg.setClear(isClear)
		if(isClear && !this.isClear){
			this.bgFever.start()
		}
		if(isRainbow && !this.isRainbow){
			this.feverFx.start()
		}
		this.isClear = isClear
		this.isRainbow = isRainbow
		
		var max = this.dancers.maxDancers
		var milestone = isClear ? max : Math.min(max - 1, Math.floor((gauge.progress || 0) * max))
		if(milestone > this.lastMilestone){
			for(var i = this.lastMilestone; i < milestone; i++){
				this.dancers.addDancer()
			}
		}else if(milestone < this.lastMilestone){
			for(var i = milestone; i < this.lastMilestone; i++){
				this.dancers.removeDancer()
			}
		}
		this.lastMilestone = milestone
	}
	
	handleHit(){
		if(this.built && !this.minimal){
			this.chibi.add(false)
		}
	}
	
	handleMiss(){
		if(this.built && !this.minimal){
			this.chibi.add(true)
		}
	}
	
	handleRoll(){
		if(this.built && !this.minimal){
			this.renda.add()
		}
	}
	
	/*
	 * Drawn into the 1280x720 frame the rest of the view uses, in the
	 * order YataiDON draws it: the scene, the band above the lanes, then
	 * everything that moves in front of them.
	 */
	draw(ctx, left, top, winW){
		if(!this.ready || !this.built){
			return
		}
		// The art is drawn for a 1280-wide frame and the window is
		// usually wider, which used to leave a black bar down each side.
		// Each layer reaches the edges in the way that suits it: the
		// band and the footer tile, the scene is scaled to cover, and
		// anything that crosses the screen crosses all of it.
		var edge = Math.max(0, ((winW || 1280) - 1280) / 2)
		var span = {left: -edge, right: 1280 + edge, width: 1280 + edge * 2}
		this.span = span
		
		ctx.save()
		ctx.translate(left, top)
		this.drawScene(ctx, span)
		this.donbg.draw(ctx, 0)
		if(!this.minimal){
			this.renda.draw(ctx)
			this.dancers.draw(ctx, span)
		}
		this.footer.draw(ctx, span)
		if(!this.minimal){
			if(this.isRainbow){
				this.feverFx.draw(ctx, span)
			}
			this.chibi.draw(ctx)
		}
		ctx.restore()
	}
	
	/*
	 * The scene below the lanes, scaled to cover the window rather than
	 * stretched to it: it is a picture, and a stretch on it shows. The
	 * DOM background this replaced did the same with background-size,
	 * and cropped the same way.
	 */
	drawScene(ctx, span){
		var top = GameBackground.TOP
		ctx.save()
		ctx.beginPath()
		ctx.rect(span.left, top, span.width, 720 - top)
		ctx.clip()
		if(span.width > 1280){
			var scale = span.width / 1280
			var middle = (top + 720) / 2
			ctx.translate(640, middle)
			ctx.scale(scale, scale)
			ctx.translate(-640, -middle)
		}
		if(!this.minimal && this.isClear){
			// The standard scene keeps drawing underneath until the
			// fever one has finished arriving.
			if(!this.bgFever.transitioned){
				this.bgNormal.draw(ctx)
			}
			this.bgFever.draw(ctx)
		}else{
			this.bgNormal.draw(ctx)
		}
		ctx.restore()
	}
}

// Where the band above the lanes has to reach. YataiDON's note lanes end
// at 360 and its background scene begins there; taiko-web's end at 322,
// so the band covers the difference rather than leaving a gap.
GameBackground.TOP = 360
