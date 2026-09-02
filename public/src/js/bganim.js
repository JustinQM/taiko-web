/*
 * YataiDON's animation primitives.
 *
 * Everything that moves in its gameplay background is one of three
 * things -- a move, a fade, or a change of frame -- declared as data in
 * the skin and driven by a shared base class. This is that class and
 * those three, ported from src/libs/animation.cpp rather than
 * approximated, because the skin's own numbers only mean anything
 * against these semantics: a delay that holds the start value rather
 * than the zero, a reverse that happens once and then finishes, a loop
 * that restarts on the frame after it ended.
 *
 * The declared animations themselves are the skin's data and arrive in
 * the background manifest with their cross-references already resolved.
 *
 * Time comes from BgAnim.now, set once a frame before anything updates.
 * The original reads the clock inside restart(); this keeps that shape
 * without threading a timestamp through every constructor.
 */
class BgAnim{
	constructor(duration, delay, loop){
		this.duration = duration
		this.delay = delay || 0
		this.delaySaved = this.delay
		this.startMs = BgAnim.now
		this.loop = !!loop
		this.isFinished = false
		// A looping animation needs no start: it is always running.
		this.isStarted = !!loop
		this.attribute = 0
	}
	
	easeIn(progress, type){
		if(type === "quadratic"){
			return progress * progress
		}else if(type === "cubic"){
			return progress * progress * progress
		}else if(type === "exponential"){
			return progress === 0 ? 0 : Math.pow(2, 10 * (progress - 1))
		}
		return progress
	}
	
	easeOut(progress, type){
		if(type === "quadratic"){
			return progress * (2 - progress)
		}else if(type === "cubic"){
			return 1 - Math.pow(1 - progress, 3)
		}else if(type === "exponential"){
			return progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
		}
		return progress
	}
	
	// Ease-in wins when both are given, which is how the skin's
	// "ease_in and ease_out" entries actually behave.
	applyEasing(progress){
		if(this.easeInType){
			return this.easeIn(progress, this.easeInType)
		}else if(this.easeOutType){
			return this.easeOut(progress, this.easeOutType)
		}
		return progress
	}
	
	update(ms){
		if(this.loop && this.isFinished){
			this.restart()
		}
	}
	
	restart(){
		this.startMs = BgAnim.now
		this.isFinished = false
		this.delay = this.delaySaved
	}
	
	start(){
		this.isStarted = true
		this.restart()
	}
	
	reset(){
		this.restart()
		this.isStarted = false
	}
	
	/*
	 * Build one of the skin's declared animations by id. They are copies:
	 * two donbg overlays can share a declaration and still run to their
	 * own clocks.
	 */
	static get(manifest, id){
		var spec = manifest && manifest.animations && manifest.animations[id]
		if(!spec){
			return new BgMove(0, {})
		}
		if(spec.type === "fade"){
			return new BgFade(spec.duration, spec)
		}else if(spec.type === "texture_change"){
			return new BgTextureChange(spec.duration, spec.textures || [], spec)
		}
		return new BgMove(spec.duration, spec)
	}
}
BgAnim.now = 0

class BgMove extends BgAnim{
	constructor(duration, opts){
		super(duration, opts.delay, opts.loop)
		this.totalDistance = opts.total_distance || 0
		this.startPosition = opts.start_position || 0
		this.easeInType = opts.ease_in
		this.easeOutType = opts.ease_out
		// reverse_delay is 0 in most of the skin, so it cannot be tested
		// for truthiness -- a zero-length wait is still a reverse.
		this.reverseDelay = opts.reverse_delay === undefined ? null : opts.reverse_delay
		this.reverseDelaySaved = this.reverseDelay
		this.distanceSaved = this.totalDistance
		this.startSaved = this.startPosition
		this.attribute = this.startPosition
	}
	
	restart(){
		super.restart()
		this.reverseDelay = this.reverseDelaySaved
		this.totalDistance = this.distanceSaved
		this.startPosition = this.startSaved
		this.attribute = this.startPosition
	}
	
	update(ms){
		if(!this.isStarted){
			return
		}
		super.update(ms)
		var elapsed = ms - this.startMs
		if(elapsed < this.delay){
			this.attribute = this.startPosition
		}else if(elapsed >= this.delay + this.duration){
			this.attribute = this.startPosition + this.totalDistance
			if(this.reverseDelay !== null){
				this.startMs = ms
				this.delay = this.reverseDelay
				this.startPosition = this.attribute
				this.totalDistance = -this.totalDistance
				this.reverseDelay = null
			}else{
				this.isFinished = true
			}
		}else{
			var progress = (elapsed - this.delay) / this.duration
			this.attribute = this.startPosition + this.totalDistance * this.applyEasing(progress)
		}
	}
}

class BgFade extends BgAnim{
	constructor(duration, opts){
		super(duration, opts.delay, opts.loop)
		this.initialOpacity = opts.initial_opacity === undefined ? 1 : opts.initial_opacity
		this.finalOpacity = opts.final_opacity === undefined ? 0 : opts.final_opacity
		this.easeInType = opts.ease_in
		this.easeOutType = opts.ease_out
		this.reverseDelay = opts.reverse_delay === undefined ? null : opts.reverse_delay
		this.reverseDelaySaved = this.reverseDelay
		this.initialSaved = this.initialOpacity
		this.finalSaved = this.finalOpacity
		this.attribute = this.initialOpacity
	}
	
	restart(){
		super.restart()
		this.reverseDelay = this.reverseDelaySaved
		this.initialOpacity = this.initialSaved
		this.finalOpacity = this.finalSaved
		this.attribute = this.initialOpacity
	}
	
	update(ms){
		if(!this.isStarted){
			return
		}
		super.update(ms)
		var elapsed = ms - this.startMs
		if(elapsed <= this.delay){
			this.attribute = this.initialOpacity
		}else if(elapsed >= this.delay + this.duration){
			this.attribute = this.finalOpacity
			if(this.reverseDelay !== null){
				this.startMs = ms
				this.delay = this.reverseDelay
				var swap = this.initialOpacity
				this.initialOpacity = this.finalOpacity
				this.finalOpacity = swap
				this.reverseDelay = null
			}else{
				this.isFinished = true
			}
		}else{
			var progress = Math.max(0, Math.min(1, (elapsed - this.delay) / this.duration))
			this.attribute = this.initialOpacity + this.applyEasing(progress) * (this.finalOpacity - this.initialOpacity)
		}
	}
}

/*
 * A frame per span of time. Written out rather than derived so a skin
 * can hold a frame for longer than the others, which several do.
 */
class BgTextureChange extends BgAnim{
	constructor(duration, frames, opts){
		super(duration, opts && opts.delay, opts && opts.loop)
		this.frames = frames
		this.attribute = frames.length ? frames[0][2] : 0
	}
	
	reset(){
		super.reset()
		if(this.frames.length){
			this.attribute = this.frames[0][2]
		}
	}
	
	update(ms){
		if(!this.isStarted){
			return
		}
		super.update(ms)
		var elapsed = ms - this.startMs
		if(elapsed < this.delay){
			return
		}
		var time = elapsed - this.delay
		if(time <= this.duration){
			for(var i = 0; i < this.frames.length; i++){
				if(this.frames[i][0] < time && time <= this.frames[i][1]){
					this.attribute = this.frames[i][2]
				}
			}
		}else{
			this.isFinished = true
		}
	}
	
	/*
	 * The common case: n frames spread evenly over a duration. Both the
	 * dancers and the chibi rebuild this whenever the song changes tempo.
	 */
	static even(duration, count, opts){
		var frames = []
		for(var i = 0; i < count; i++){
			frames.push([duration / count * i, duration / count * (i + 1), i])
		}
		return new BgTextureChange(duration, frames, opts)
	}
}
