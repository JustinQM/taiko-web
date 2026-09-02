/*
 * The gameplay background.
 *
 * Modelled on YataiDON's, which its skin drives from Lua: a layered
 * background, a fever variant that takes over once the gauge reaches
 * clear, a footer, and up to five dancers along the bottom moving in time
 * with the song.
 *
 * Everything here is optional. The art is private, so the public build
 * has no manifest, creates nothing and draws nothing -- the game runs, it
 * simply has a plain background.
 *
 * Frame counts and sizes come from assets/backgrounds.json rather than
 * being repeated here as constants; the strips and the manifest are
 * written by the same tool.
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
		
		var choice = GameBackground.choose(view.controller.selectedSong, this.manifest)
		this.bgSet = choice.bgSet
		this.feverSet = choice.feverSet
		this.dancerSet = choice.dancerSet
		this.footer = choice.footer
		this.donSet = choice.donSet
		this.donHalf = view.player === 2 ? 2 : 1
		
		this.dancers = this.makeDancers()
		this.startedAt = null
		this.fever = false
		this.ready = true
	}
	
	/*
	 * Which background a song gets, and everything that follows from it.
	 *
	 * Taken from the song rather than at random, so a song looks the same
	 * every time it is played and two players in a session see the same
	 * thing. Shared with the loader, which has to know what to fetch
	 * before this exists -- if the two disagreed, the song would load one
	 * background and draw another.
	 */
	static choose(song, manifest){
		var seed = GameBackground.seed(song)
		var pick = (list, n) => (list && list.length) ? list[n % list.length] : null
		return {
			bgSet: pick(manifest.bgSets, seed),
			feverSet: pick(manifest.feverSets, seed + 1),
			dancerSet: pick(manifest.dancerSets, seed + 2),
			footer: seed % 3,
			donSet: seed % 3
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
	 * The strips one song needs. All of them together are 12MB, which is
	 * most of what the game used to load before the title screen; a song
	 * needs under three, and loads them while its loading screen is up
	 * rather than while it is being played.
	 */
	static assetsFor(song, manifest){
		if(!manifest || !manifest.assets){
			return []
		}
		var choice = GameBackground.choose(song, manifest)
		var wanted = [
			"yatai_bg_normal" + choice.bgSet,
			"yatai_bg_normal" + choice.bgSet + "_overlay",
			"yatai_bg_footer" + choice.footer
		]
		for(var set of [choice.feverSet]){
			wanted.push("yatai_bg_fever" + set, "yatai_bg_fever" + set + "_overlay",
				"yatai_bg_fever" + set + "_mountain", "yatai_bg_fever" + set + "_wave",
				"yatai_bg_fever" + set + "_footer")
		}
		for(var half of [1, 2]){
			for(var part of ["background", "overlay"]){
				wanted.push("yatai_bg_don" + choice.donSet + "_" + half + "_" + part)
			}
		}
		for(var i = 0; i < 5; i++){
			for(var part of ["start", "loop", "end"]){
				wanted.push("yatai_bg_dancer" + choice.dancerSet + "_" + i + "_" + part)
			}
		}
		// The manifest is the record of what exists: a set with fewer than
		// five dancers is normal rather than a missing file.
		return wanted.filter(name => name in manifest.assets)
	}
	
	seedFrom(song){
		var text = (song && (song.hash || song.title)) || ""
		var seed = 0
		for(var i = 0; i < text.length; i++){
			seed = (seed * 31 + text.charCodeAt(i)) % 100003
		}
		return seed
	}
	
	pick(list, seed){
		if(!list || !list.length){
			return null
		}
		return list[seed % list.length]
	}
	
	sheet(name){
		var entry = this.manifest.assets[name]
		var img = assets.image[name]
		if(!entry || !img || !img.complete || !img.naturalWidth){
			return null
		}
		var frames = entry.frames || 1
		return {
			img: img,
			frames: frames,
			w: img.naturalWidth / frames,
			h: img.naturalHeight
		}
	}
	
	/*
	 * One dancer per slot the set actually has. Sets vary: some have five,
	 * some fewer, and a missing slot is normal rather than a fault.
	 */
	makeDancers(){
		var dancers = []
		for(var i = 0; i < 5; i++){
			var loop = this.sheet("yatai_bg_dancer" + this.dancerSet + "_" + i + "_loop")
			if(!loop){
				continue
			}
			dancers.push({
				index: i,
				start: this.sheet("yatai_bg_dancer" + this.dancerSet + "_" + i + "_start"),
				loop: loop,
				end: this.sheet("yatai_bg_dancer" + this.dancerSet + "_" + i + "_end")
			})
		}
		return dancers
	}
	
	/*
	 * Dancers move with the music: YataiDON gives a loop frame
	 * (60000 / bpm) / 2, so one full cycle is half a beat per frame rather
	 * than a fixed rate.
	 */
	frameDuration(){
		var interval = this.view.beatInterval || 512
		return interval / 2
	}
	
	update(ms, gaugeCleared){
		if(!this.ready){
			return
		}
		if(this.startedAt === null){
			this.startedAt = ms
		}
		this.ms = ms
		this.fever = !!gaugeCleared
	}
	
	frameAt(sheet, elapsed, loop){
		if(!sheet){
			return 0
		}
		var frame = Math.floor(elapsed / this.frameDuration())
		if(loop){
			return ((frame % sheet.frames) + sheet.frames) % sheet.frames
		}
		return Math.min(sheet.frames - 1, Math.max(0, frame))
	}
	
	drawFrame(ctx, sheet, frame, x, y, w, h){
		if(!sheet){
			return
		}
		ctx.drawImage(sheet.img, frame * sheet.w, 0, sheet.w, sheet.h,
			x, y, w === undefined ? sheet.w : w, h === undefined ? sheet.h : h)
	}
	
	/*
	 * Drawn into the 1280x720 frame the rest of the view uses, so it lines
	 * up with everything else whatever the window is doing.
	 */
	draw(ctx, left, top){
		if(!this.ready){
			return
		}
		ctx.save()
		ctx.translate(left, top)
		// Dimmed while the gauge is failing, which the DOM background did
		// with a class.
		if(this.view.darkDonBg){
			ctx.globalAlpha *= 0.55
		}
		this.drawTopBand(ctx)
		this.drawLayers(ctx)
		this.drawDancers(ctx)
		this.drawFooter(ctx)
		ctx.restore()
	}
	
	/*
	 * The band above the note lanes, behind the header and the gauge.
	 * The art is 656 wide and meant to tile, so it is repeated across
	 * rather than stretched.
	 */
	drawTopBand(ctx){
		var name = "yatai_bg_don" + this.donSet + "_" + this.donHalf
		var background = this.sheet(name + "_background")
		var overlay = this.sheet(name + "_overlay")
		if(!background){
			return
		}
		var frame = this.frameAt(background, this.ms - this.startedAt, true)
		// Tiled both ways: the art is 656x184 and the band above the lanes
		// is the full width and taller than one tile, so anything less
		// leaves the header sitting on bare canvas.
		for(var y = GameBackground.TOP - background.h; y > -background.h; y -= background.h){
			for(var x = 0; x < 1280; x += background.w){
				this.drawFrame(ctx, background, frame, x, y)
			}
		}
		if(overlay){
			var overlayFrame = this.frameAt(overlay, this.ms - this.startedAt, true)
			for(var x = 0; x < 1280; x += overlay.w){
				this.drawFrame(ctx, overlay, overlayFrame, x, GameBackground.TOP - overlay.h)
			}
		}
	}
	
	/*
	 * The band below the note lanes, which is most of what you see. It
	 * changes to the fever art once the gauge reaches clear -- the one
	 * part of the background that reacts to how the song is going.
	 */
	drawLayers(ctx){
		var elapsed = this.ms - this.startedAt
		var y = GameBackground.TOP
		var prefix = this.fever
			? "yatai_bg_fever" + this.feverSet
			: "yatai_bg_normal" + this.bgSet
		
		var background = this.sheet(prefix)
		if(background){
			var frame = background.frames > 1 ? this.frameAt(background, elapsed, true) : 0
			this.drawFrame(ctx, background, frame, 0, y, 1280, background.h)
		}
		
		if(this.fever){
			// The fever art is built from pieces rather than one image:
			// hills behind, water in front, and a glow over the top.
			var mountain = this.sheet(prefix + "_mountain")
			var wave = this.sheet(prefix + "_wave")
			if(mountain){
				this.drawFrame(ctx, mountain, 0, (1280 - mountain.w) / 2,
					y + background.h - mountain.h)
			}
			if(wave){
				// Drifts sideways with the beat, so the water moves.
				var drift = (elapsed / 40) % wave.w
				for(var x = -drift; x < 1280; x += wave.w){
					this.drawFrame(ctx, wave, 0, x, 720 - wave.h)
				}
			}
		}
		
		var overlay = this.sheet(prefix + "_overlay")
		if(overlay){
			ctx.save()
			ctx.globalAlpha *= 0.75
			this.drawFrame(ctx, overlay, 0, (1280 - overlay.w) / 2, y, overlay.w, overlay.h)
			ctx.restore()
		}
	}
	
	/*
	 * Dancers bounce in from below when play starts -- up 350 over half a
	 * beat eased out, then down 140 eased in, after a 500ms wait -- and
	 * loop from there. The numbers are the skin's.
	 */
	drawDancers(ctx){
		if(!this.dancers.length){
			return
		}
		var elapsed = this.ms - this.startedAt
		var beat = this.view.beatInterval || 512
		var spacing = 1280 / (this.dancers.length + 1)
		
		for(var i = 0; i < this.dancers.length; i++){
			var dancer = this.dancers[i]
			var sheet = dancer.loop
			if(!sheet){
				continue
			}
			// Staggered, so five dancers do not arrive as one block.
			var since = elapsed - 500 - i * (beat / 8)
			var lift = 0
			if(since < 0){
				lift = -200
			}else if(since < beat / 2){
				var t = since / (beat / 2)
				lift = -200 + 350 * (t * (2 - t))
			}else if(since < beat){
				var t = (since - beat / 2) / (beat / 2)
				lift = 150 - 140 * (t * t)
			}else{
				lift = 10
			}
			
			var frame = this.frameAt(sheet, Math.max(0, since), true)
			var x = spacing * (i + 1) - sheet.w / 2
			var y = GameBackground.DANCER_BASE - sheet.h - lift
			this.drawFrame(ctx, sheet, frame, x, y)
		}
	}
	
	drawFooter(ctx){
		// The fever art brings its own footer; otherwise the plain one.
		var sheet = this.fever
			? this.sheet("yatai_bg_fever" + this.feverSet + "_footer")
			: null
		sheet = sheet || this.sheet("yatai_bg_footer" + this.footer)
		if(sheet){
			this.drawFrame(ctx, sheet, 0, 0, 720 - sheet.h, 1280, sheet.h)
		}
	}
}

// Where the background band starts and where the dancers stand, in the
// 1280x720 frame everything else is drawn in.
GameBackground.TOP = 322
GameBackground.DANCER_BASE = 700
