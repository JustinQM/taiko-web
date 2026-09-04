/*
 * The difficulty search: browse by course and star level instead of by
 * name.
 *
 * A transcription of YataiDON's DiffSortSelect (src/objects/song_select/
 * diff_sort.cpp) and the art that goes with it. Two screens over a
 * dimmed wheel -- pick a course, pick a star level -- then a three-way
 * confirmation prompt, and the folder behind fills with what was asked
 * for.
 *
 * Everything positional comes from the skin rather than from taste.
 * Graphics/song_select/diff_sort/texture.json gives each texture a
 * top-left in the 1280x720 frame, skin_config.json gives the spacings,
 * and animation.json gives the timings; YataiDON reads all three at
 * runtime and taiko-web has no equivalent indirection, so they are
 * written out below and this file is what keeps them true.
 */
class DiffSortSelect{

	// texture.json. One entry per texture, x and y its top-left; a list
	// where the skin gives a texture more than one position and draws it
	// by index.
	static pos = {
		background:              {x: 242, y: 30},
		back:                    {x: 295, y: 132},
		back_outline:            {x: 295, y: 132},
		box:                     {x: 388, y: 132},
		box_highlight:           {x: 388, y: 132},
		box_outline:             {x: 388, y: 132},
		box_diff:                {x: 388, y: 92},
		// Where the skin's own star_select_text and star_limit sat, and
		// where the course name is written inside the level box: all
		// three are drawn as text now, at the same places.
		heading:                 {x: 412, y: 50},
		limit:                   {x: 455, y: 105},
		level_box:               {x: 356, y: 160},
		diff:                    {x: 414, y: 170},
		star_num:                {x: 734, y: 175},
		star:                    {x: 435, y: 260},
		pongos:                  {x: 492, y: 400},
		small_box:               {x: 292, y: 405},
		small_box_outline:       {x: 292, y: 405},
		small_box_highlight:     {x: 292, y: 405},
		stat_bg_1p:              {x: 25, y: 156},
		stat_overlay:            {x: 25, y: 156},
		stat_diff:               {x: 36, y: 195},
		stat_starx:              {x: 110, y: 195},
		stat_num:                [{x: 130, y: 280}],
		stat_num_small:          [{x: 206, y: 346}, {x: 206, y: 392}],
		stat_num_star:           [{x: 166, y: 327}, {x: 131, y: 327}, {x: 131, y: 377}],
		arrow:                   [{x: 356, y: 240}, {x: 874, y: 240}]
	}

	// skin_config.json, the diff_sort_* keys.
	static margin1 = 25        // the star counts, large
	static margin2 = 23        // the total, large
	static margin3 = 10        // the totals, small
	static boxOffset = 100     // between difficulty boxes
	static smallBoxOffset = 245 // between confirmation boxes
	static starSpacing = 40.5  // between stars in the row
	static statNumStar = {x: 70, y: -108}  // the "x N" beside the star mark

	// The digit strips keep the skin's own layout: one row of ten, each
	// cell this size. The frame strips are uniform, so their cell width
	// is worked out from the image instead.
	static digits = {
		yatai_diff_sort_stat_num: {w: 28, h: 36},
		yatai_diff_sort_stat_num_small: {w: 16, h: 19},
		yatai_diff_sort_stat_num_star: {w: 36, h: 44}
	}

	// animation.json, ids 19-25 and 29-30.
	static anim = {
		resize: {duration: 283, from: 0.2, to: 1},
		fadeIn: {duration: 283},
		flicker: {duration: 133},
		bounce: [
			{distance: 30, duration: 116.67, delay: 0, easeOut: true},
			{distance: 30, duration: 116.67, delay: 116.67, easeOut: false},
			{distance: 10, duration: 83.33, delay: 233.34, easeOut: true},
			{distance: 10, duration: 83.33, delay: 316.67, easeOut: false}
		],
		arrow: {duration: 1000, distance: 25}
	}

	static numBoxes = 6

	// The boxes the labels are written across, so the text can be placed
	// and fitted without measuring the artwork every frame.
	static size = {
		background: {w: 796, h: 542},
		back: {w: 80, h: 320},
		box: {w: 83, h: 378},
		heading: {w: 456, h: 62},
		limit: {w: 370, h: 44},
		levelBox: {w: 568, h: 192},
		diff: {w: 312, h: 70},
		smallBox: {w: 206, h: 98},
		emblem: 86
	}

	// The return arrow occupies the top of the back box; the word goes
	// below it, in the part the import blanked out.
	static backTextTop = 62

	// Inside the statistics panel's white frame. The panel image is 260
	// wide but carries transparent padding down its right side, so this
	// is measured off where the frame is actually drawn rather than
	// worked out from the image.
	static panelRight = 252

	/*
	 * The panel below its header box, which the skin no longer draws.
	 *
	 * The skin has two crown rows at a pitch of fifty and no room for a
	 * third; these are three at thirty-five, which is what fits between
	 * the header box (ending at 271) and the bottom of the frame (at
	 * 427). The total above them moves up a little to pay for it, and the
	 * counts are drawn smaller than the skin's to sit in a shorter row.
	 */
	static panel = {
		totalShift: -6,
		rowTop: 314,
		rowPitch: 35,
		rowMiddle: 16,
		crownX: 62,
		crownSize: 34,
		countRight: 165,
		countScale: 0.75,
		slashX: 190,
		overRight: 242,
		overDrop: 10
	}

	/*
	 * prev is the last search this session made, which box 5 repeats.
	 * Null before there has been one, in which case that box cancels --
	 * which is what YataiDON's {-1, -1} does there too.
	 */
	constructor(songSelect, prev, ms){
		this.songSelect = songSelect
		this.navigator = songSelect.navigator
		this.prev = prev || null

		this.selectedBox = -1
		this.selectedLevel = 1
		this.inLevelSelect = false
		this.confirmation = false
		this.confirmIndex = 1

		this.startMS = ms
		this.screenMS = ms
		this.bounceMS = 0

		this.stats = this.navigator.diffSortStats()
		// How far each course's stars go, taken from what the library
		// actually holds rather than from the five fixed limits the
		// skin's artwork was cut for.
		this.limits = this.navigator.diffSortLimits(this.stats)
		// Each course's totals over every level, which is what the panel
		// shows while the cursor is still on the difficulty boxes.
		// YataiDON sums these once in its own constructor too.
		this.courseStats = this.stats.map(levels => {
			var sum = {total: 0, clears: 0, fullCombos: 0, donderfuls: 0}
			levels.forEach(cell => {
				sum.total += cell.total
				sum.clears += cell.clears
				sum.fullCombos += cell.fullCombos
				sum.donderfuls += cell.donderfuls
			})
			return sum
		})
	}

	// ------------------------------------------------------------- input

	inputLeft(){
		if(this.confirmation){
			this.confirmIndex = Math.max(this.confirmIndex - 1, 0)
		}else if(this.inLevelSelect){
			this.selectedLevel = Math.max(this.selectedLevel - 1, 1)
		}else{
			this.selectedBox = Math.max(this.selectedBox - 1, -1)
		}
	}

	inputRight(){
		if(this.confirmation){
			this.confirmIndex = Math.min(this.confirmIndex + 1, 2)
		}else if(this.inLevelSelect){
			this.selectedLevel = Math.min(this.selectedLevel + 1, this.limits[this.selectedBox])
		}else{
			this.selectedBox = Math.min(this.selectedBox + 1, DiffSortSelect.numBoxes - 1)
		}
	}

	/*
	 * Put the cursor somewhere directly, which is what a click on a box
	 * the cursor is not already on means. The drum can only step, so
	 * nothing reaches this except the mouse.
	 */
	inputIndex(index){
		if(this.confirmation){
			this.confirmIndex = Math.max(0, Math.min(index, 2))
		}else if(this.inLevelSelect){
			this.selectedLevel = Math.max(1, Math.min(index, this.limits[this.selectedBox]))
		}else{
			this.selectedBox = Math.max(-1, Math.min(index, DiffSortSelect.numBoxes - 1))
		}
	}

	/*
	 * Don. Returns null while the picker is still being used, a
	 * {course, level} to search for, or {cancel: true} to close it and
	 * leave the wheel alone.
	 *
	 * The fall-through is YataiDON's and is deliberate: dismissing the
	 * prompt with its leftmost box does not return, so control reaches
	 * the tail and enters level select again -- which replays its
	 * animation and its voice line, and is what "back to the stars"
	 * looks like there.
	 */
	inputSelect(ms){
		if(this.confirmation){
			if(this.confirmIndex === 0){
				this.confirmation = false
			}else if(this.confirmIndex === 1){
				return {course: this.selectedBox, level: this.selectedLevel}
			}else if(this.confirmIndex === 2){
				this.confirmation = false
				this.inLevelSelect = false
				this.screenMS = ms
				return null
			}
		}else if(this.inLevelSelect){
			this.confirmation = true
			this.confirmIndex = 1
			this.bounceMS = ms
			this.songSelect.playSound("v_diffsort_confirm", 0.1)
			return null
		}
		if(this.selectedBox === -1){
			return {cancel: true}
		}
		if(this.selectedBox === DiffSortSelect.numBoxes - 1){
			return this.prev ? {course: this.prev.course, level: this.prev.level} : {cancel: true}
		}
		this.songSelect.playSound("v_diffsort_level", 0.1)
		this.inLevelSelect = true
		this.screenMS = ms
		this.selectedLevel = Math.min(this.selectedLevel, this.limits[this.selectedBox])
		return null
	}

	// ------------------------------------------------------- mouse hits

	/*
	 * What is under the pointer, in frame coordinates. Returns an action
	 * the caller can apply -- the same three the drum has, so a click
	 * goes through exactly the path a press does.
	 */
	hit(x, y){
		var P = DiffSortSelect.pos
		if(this.inLevelSelect){
			if(this.confirmation){
				var small = DiffSortSelect.size.smallBox
				for(var i = 0; i < 3; i++){
					if(this.inRect(x, y, P.small_box.x + i * DiffSortSelect.smallBoxOffset, P.small_box.y, small.w, small.h)){
						return {index: i, select: true}
					}
				}
				return null
			}
			// The arrows step the level; the box itself is the way on,
			// which is the only part of this screen the drum reaches
			// with a don.
			if(this.selectedLevel > 1 && this.inRect(x, y, P.arrow[0].x, P.arrow[0].y, 70, 70)){
				return {move: -1}
			}
			if(this.selectedLevel < this.limits[this.selectedBox] && this.inRect(x, y, P.arrow[1].x, P.arrow[1].y, 70, 70)){
				return {move: 1}
			}
			if(this.inRect(x, y, P.level_box.x, P.level_box.y,
					DiffSortSelect.size.levelBox.w, DiffSortSelect.size.levelBox.h)){
				return {select: true}
			}
			return null
		}
		if(this.inRect(x, y, P.back.x, P.back.y, DiffSortSelect.size.back.w, DiffSortSelect.size.back.h)){
			return {index: -1, select: true}
		}
		var box = DiffSortSelect.size.box
		for(var i = 0; i < DiffSortSelect.numBoxes; i++){
			if(this.inRect(x, y, P.box.x + i * DiffSortSelect.boxOffset, P.box.y, box.w, box.h)){
				return {index: i, select: true}
			}
		}
		return null
	}

	inRect(x, y, rx, ry, w, h){
		return x >= rx && x <= rx + w && y >= ry && y <= ry + h
	}

	// -------------------------------------------------------- animation

	easeOut(t){
		return 1 - (1 - t) * (1 - t)
	}

	easeIn(t){
		return t * t
	}

	clamp01(value){
		return value < 0 ? 0 : value > 1 ? 1 : value
	}

	// The screen's scale-in, from a fifth of its size.
	bgScale(ms){
		var a = DiffSortSelect.anim.resize
		var t = this.clamp01((ms - this.screenMS) / a.duration)
		return a.from + (a.to - a.from) * this.easeOut(t)
	}

	fadeIn(ms){
		return this.easeOut(this.clamp01((ms - this.screenMS) / DiffSortSelect.anim.fadeIn.duration))
	}

	// The cursor outline, pulsing on and off. A fade that loops with no
	// delay at either end is a triangle over twice its duration.
	flicker(ms){
		var d = DiffSortSelect.anim.flicker.duration
		var t = ((ms - this.startMS) % (d * 2)) / d
		return t > 1 ? 2 - t : t
	}

	// The prompt's double bounce: thirty pixels up and down, then ten.
	bounce(ms){
		if(!this.bounceMS){
			return 0
		}
		var elapsed = ms - this.bounceMS
		var y = 0
		DiffSortSelect.anim.bounce.forEach((step, i) => {
			var t = this.clamp01((elapsed - step.delay) / step.duration)
			var value = (step.easeOut ? this.easeOut(t) : this.easeIn(t)) * step.distance
			// up, down, up, down
			y += i % 2 === 0 ? -value : value
		})
		return y
	}

	arrowPulse(ms){
		var d = DiffSortSelect.anim.arrow.duration
		var t = ((ms - this.startMS) % (d * 2)) / d
		return t > 1 ? 2 - t : t
	}

	// ---------------------------------------------------------- drawing

	/*
	 * One texture, by the name it was imported under, at the position the
	 * skin gives it.
	 *
	 * config takes the same shape YataiDON's draw_texture options do: x
	 * and y are offsets from that position rather than absolutes, index
	 * picks between the positions of a texture that has several, frame
	 * picks a column of a strip, fade is opacity, and scale grows the
	 * texture about its own center.
	 */
	tex(ctx, name, config){
		config = config || {}
		var img = assets.image["yatai_diff_sort_" + name]
		// The public repo ships no game assets, so on a build without
		// them these are Image objects that never loaded. Drawing one
		// throws, and the picker itself works without them.
		if(!img || !img.naturalWidth){
			return
		}
		// The panel's rows are laid out here rather than taken from the
		// skin, so they say where they go instead of offsetting from it.
		var pos = config.at || DiffSortSelect.pos[name]
		if(Array.isArray(pos)){
			pos = pos[config.index || 0]
		}
		if(!pos){
			return
		}
		var sx = 0
		var sy = 0
		var sw = img.width
		var sh = img.height
		if(config.crop){
			sx = config.crop.x
			sw = config.crop.w
			sh = config.crop.h
		}else if(config.frames){
			sw = img.width / config.frames
			sx = sw * (config.frame || 0)
		}
		var x = this.frameLeft + pos.x + (config.x || 0)
		var y = this.frameTop + pos.y + (config.y || 0)
		var w = sw
		var h = sh
		if(config.scale && config.scale !== 1){
			x += w * (1 - config.scale) / 2
			y += h * (1 - config.scale) / 2
			w *= config.scale
			h *= config.scale
		}
		var fade = "fade" in config ? config.fade : 1
		if(fade <= 0){
			return
		}
		ctx.save()
		if(fade < 1){
			ctx.globalAlpha = fade
		}
		if(config.mirror){
			ctx.translate(x + w, y)
			ctx.scale(-1, 1)
			ctx.drawImage(img, sx, sy, sw, sh, 0, 0, w, h)
		}else{
			ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h)
		}
		ctx.restore()
	}

	/*
	 * A label, in the game's own lettering.
	 *
	 * The skin writes this screen's words into its artwork and only in
	 * Japanese, so none of those layers are imported and every word here
	 * is drawn instead. Two layers, black outline under white fill, is
	 * how the wheel below writes everything else.
	 */
	label(ctx, text, config){
		this.songSelect.draw.layeredText({
			ctx: ctx,
			text: text,
			fontSize: config.size,
			fontFamily: this.songSelect.font,
			x: config.x,
			y: config.y,
			width: config.width,
			align: "center",
			baseline: "middle",
			letterSpacing: config.letterSpacing
		}, [
			{outline: config.outline || "#000", letterBorder: config.size * 0.28},
			{fill: config.fill || "#fff"}
		])
	}

	/*
	 * A label written up the length of one of the difficulty boxes.
	 *
	 * The boxes are slats, eighty-odd wide and four hundred tall, and the
	 * skin's own labels run down them as stacked Japanese characters.
	 * Latin script does not stack, so it is turned on its side instead
	 * and reads bottom to top.
	 */
	verticalLabel(ctx, text, config){
		ctx.save()
		ctx.translate(config.x, config.y)
		ctx.rotate(-Math.PI / 2)
		this.label(ctx, text, {
			x: 0, y: 0,
			size: config.size,
			width: config.width,
			fill: config.fill,
			outline: config.outline
		})
		ctx.restore()
	}

	/*
	 * A number, drawn from one of the digit strips.
	 *
	 * The skin lays the ten digits out in a row and the game picks a cell
	 * per character, so the spacing is the skin's margin rather than the
	 * cell width -- the digits overlap slightly by design.
	 */
	number(ctx, name, value, config){
		config = config || {}
		var cell = DiffSortSelect.digits["yatai_diff_sort_" + name]
		var text = String(value)
		for(var i = 0; i < text.length; i++){
			var digit = text.charCodeAt(i) - 48
			if(digit < 0 || digit > 9){
				continue
			}
			this.tex(ctx, name, {
				index: config.index,
				at: config.at,
				scale: config.scale,
				crop: {x: cell.w * digit, w: cell.w, h: cell.h},
				x: (config.x || 0) + (config.spacing || 0) * i,
				y: config.y || 0,
				fade: config.fade
			})
		}
	}

	// Centered on the texture's own position, which is how every count in
	// the panel but the star level is placed.
	centeredNumber(ctx, name, value, spacing, config){
		config = config || {}
		var width = String(value).length * spacing
		this.number(ctx, name, value, {
			index: config.index,
			spacing: spacing,
			x: -(width / 2) + (config.x || 0),
			y: config.y,
			fade: config.fade
		})
	}

	/*
	 * The panel down the left: which course, at which level, how many
	 * charts there are, and how many of them you have cleared and full
	 * comboed.
	 *
	 * With no level chosen yet it shows the course's totals summed over
	 * every level, which is what the difficulty boxes are standing on.
	 *
	 * Only ever drawn for one of the five real courses. YataiDON's own
	 * version has a branch for the sixth box, the one that repeats the
	 * last search, but neither screen calls this while that box is
	 * selected -- so it and its stat_prev art are left out here.
	 */
	drawStatistics(ctx){
		this.tex(ctx, "stat_bg_1p")
		this.tex(ctx, "stat_overlay")
		this.tex(ctx, "stat_diff", {frame: this.selectedBox, frames: 5})

		if(this.inLevelSelect){
			this.tex(ctx, "stat_starx")
			// Right-aligned against the star mark rather than centered.
			var text = String(this.selectedLevel)
			this.number(ctx, "stat_num_star", text, {
				spacing: DiffSortSelect.margin1,
				x: DiffSortSelect.statNumStar.x - text.length * DiffSortSelect.margin1,
				y: DiffSortSelect.statNumStar.y
			})
			var cell = this.cell(this.selectedBox, this.selectedLevel)
		}else{
			var cell = this.courseStats[this.selectedBox]
				|| {total: 0, clears: 0, fullCombos: 0, donderfuls: 0}
		}

		this.centeredNumber(ctx, "stat_num", cell.total, DiffSortSelect.margin2,
			{y: DiffSortSelect.panel.totalShift})
		// Where the skin wrote 全 N 曲 the kanji have been cleared out of
		// the overlay, so the count is labeled here instead. The two
		// crown rows below it are "N / N" either way and need no word.
		//
		// One kanji fitted between the number and the panel's edge; a
		// word does not, and the number is centered so it grows towards
		// that edge as the count gains a digit. So the label takes
		// whatever room is left rather than a fixed spot, and is squeezed
		// to fit it -- a course total runs to four digits and leaves
		// noticeably less than a single level's does.
		var overlay = DiffSortSelect.pos.stat_bg_1p
		var right = this.numberRight(cell.total)
		var room = DiffSortSelect.panelRight - right - 12
		this.label(ctx, strings.diffSort.songs, {
			x: this.frameLeft + right + 6 + room / 2,
			y: this.frameTop + overlay.y + 141 + DiffSortSelect.panel.totalShift,
			size: 20,
			width: room
		})
		this.drawCrownRows(ctx, cell)
	}

	/*
	 * One row per crown: how many of these charts you have cleared, full
	 * comboed and donderfulled, each over the total.
	 *
	 * The skin draws two rows and bakes their crowns and slashes into the
	 * overlay. We show three -- a donderful is worth seeing, and the
	 * counts are cumulative anyway, so a row that is always a subset of
	 * the one above it reads naturally underneath it. Three rows do not
	 * fit at the skin's pitch, so the overlay keeps only its header box
	 * and the rows are laid out here instead.
	 *
	 * Cumulative: every crown counts in its own row and in every row
	 * above. A full combo is a clear, and a donderful is both.
	 */
	drawCrownRows(ctx, cell){
		var P = DiffSortSelect.panel
		var rows = [
			{crown: "silver", value: cell.clears},
			{crown: "gold", value: cell.fullCombos},
			{crown: "rainbow", value: cell.donderfuls}
		]
		var countSpacing = DiffSortSelect.margin1 * P.countScale
		rows.forEach((row, i) => {
			var y = P.rowTop + i * P.rowPitch
			// Through the game's own crown drawing rather than straight
			// from the image: it picks the right set, and it falls back
			// to the vector path on a build that has no crown art.
			this.songSelect.draw.crown({
				ctx: ctx,
				type: row.crown,
				variant: "small",
				x: this.frameLeft + P.crownX,
				y: this.frameTop + y + P.rowMiddle,
				size: P.crownSize,
				ratio: this.songSelect.ratio / this.songSelect.pixelRatio
			})
			// The count and the total it is out of, both right-aligned so
			// the three rows line up however many digits they run to.
			var count = String(row.value)
			this.number(ctx, "stat_num_star", count, {
				at: {x: P.countRight - count.length * countSpacing, y: y},
				spacing: countSpacing,
				scale: P.countScale
			})
			this.label(ctx, "/", {
				x: this.frameLeft + P.slashX,
				y: this.frameTop + y + P.rowMiddle,
				size: 22,
				width: 20
			})
			var total = String(cell.total)
			this.number(ctx, "stat_num_small", total, {
				at: {x: P.overRight - total.length * DiffSortSelect.margin3,
					y: y + P.overDrop},
				spacing: DiffSortSelect.margin3
			})
		})
	}

	/*
	 * What each box is called. The first five are the course names the
	 * difficulty screen already uses -- Extreme rather than Oni, since
	 * that is what this game calls it everywhere else -- and the sixth
	 * is the search made last time.
	 */
	boxLabel(index){
		if(index === DiffSortSelect.numBoxes - 1){
			return strings.diffSort.previous
		}
		return [strings.easy, strings.normal, strings.hard, strings.oni,
			strings.ura][index] || ""
	}

	/*
	 * The right-hand edge of the big total, which is drawn centered and so
	 * moves with how many digits it has.
	 */
	numberRight(value){
		var spacing = DiffSortSelect.margin2
		var cellWidth = DiffSortSelect.digits.yatai_diff_sort_stat_num.w
		var digits = String(value).length
		return DiffSortSelect.pos.stat_num[0].x
			+ (digits * spacing) / 2 - spacing + cellWidth
	}

	cell(course, level){
		var levels = this.stats[course]
		var cell = levels && levels[level]
		return cell || {total: 0, clears: 0, fullCombos: 0, donderfuls: 0}
	}

	drawDiffSelect(ctx, ms){
		var fade = this.fadeIn(ms)
		var offset = DiffSortSelect.boxOffset
		var size = DiffSortSelect.size
		var P = DiffSortSelect.pos
		this.tex(ctx, "background", {scale: this.bgScale(ms)})
		this.tex(ctx, "back", {fade: fade})

		ctx.save()
		ctx.globalAlpha = fade
		this.verticalLabel(ctx, strings.back, {
			x: this.frameLeft + P.back.x + size.back.w / 2,
			y: this.frameTop + P.back.y + DiffSortSelect.backTextTop
				+ (size.back.h - DiffSortSelect.backTextTop) / 2,
			size: 38,
			width: size.back.h - DiffSortSelect.backTextTop - 24
		})
		ctx.restore()

		for(var i = 0; i < DiffSortSelect.numBoxes; i++){
			var on = i === this.selectedBox
			this.tex(ctx, on ? "box_highlight" : "box", {x: offset * i, fade: fade})
		}
		// The labels are drawn after every box, so a neighbor's box art
		// cannot land on top of one of them.
		ctx.save()
		ctx.globalAlpha = fade
		for(var i = 0; i < DiffSortSelect.numBoxes; i++){
			var on = i === this.selectedBox
			this.verticalLabel(ctx, this.boxLabel(i), {
				x: this.frameLeft + P.box.x + offset * i + size.box.w / 2,
				y: this.frameTop + P.box.y + size.box.h / 2 + 22,
				size: 42,
				width: size.box.h - 70,
				// The selected box is bright yellow, so its label takes
				// the darker outline the skin gave it there.
				outline: on ? "#8a4b12" : "#000"
			})
		}
		ctx.restore()

		var flicker = this.flicker(ms)
		if(this.selectedBox === -1){
			this.tex(ctx, "back_outline", {fade: flicker})
		}else{
			this.tex(ctx, "box_outline", {x: offset * this.selectedBox, fade: flicker})
		}

		// The course emblems sit above the boxes and do not fade with
		// them. Only the five real courses have one; the sixth box is
		// the last search repeated.
		for(var i = 0; i < 5; i++){
			this.tex(ctx, "box_diff", {frame: i, frames: 5, x: offset * i})
		}

		if(this.selectedBox !== -1 && this.selectedBox !== DiffSortSelect.numBoxes - 1){
			this.drawStatistics(ctx)
		}
	}

	/*
	 * The big star count above the row of stars.
	 *
	 * The skin has ten of these drawn, one per level, and the library
	 * has nothing above ten -- but the cap is the library's now rather
	 * than the skin's, so anything past the artwork falls back to the
	 * same lettering the rest of the screen uses.
	 */
	drawLevelNumber(ctx, fade){
		var P = DiffSortSelect.pos
		if(this.selectedLevel <= 10){
			this.tex(ctx, "star_num", {frame: this.selectedLevel - 1, frames: 10, fade: fade})
			return
		}
		ctx.save()
		ctx.globalAlpha = fade
		this.label(ctx, "\u2605" + this.selectedLevel, {
			x: this.frameLeft + P.star_num.x + 56,
			y: this.frameTop + P.star_num.y + 30,
			size: 52,
			width: 112
		})
		ctx.restore()
	}

	/*
	 * How far apart the stars in the row sit. The skin's spacing fits ten
	 * of them across the level box; past that they are drawn closer
	 * together rather than out of it.
	 */
	starSpacing(){
		var spacing = DiffSortSelect.starSpacing
		var star = 44
		var available = DiffSortSelect.pos.level_box.x + DiffSortSelect.size.levelBox.w - 24
			- DiffSortSelect.pos.star.x - star
		var count = this.selectedLevel - 1
		if(count > 0 && count * spacing > available){
			spacing = available / count
		}
		return spacing
	}

	drawLevelSelect(ctx, ms){
		var fade = this.fadeIn(ms)
		this.tex(ctx, "background", {scale: this.bgScale(ms)})
		var size = DiffSortSelect.size
		var P = DiffSortSelect.pos
		this.label(ctx, this.confirmation ? strings.diffSort.confirm : strings.diffSort.chooseStars, {
			x: this.frameLeft + P.heading.x + size.heading.w / 2,
			y: this.frameTop + P.heading.y + size.heading.h / 2,
			size: 44,
			width: size.heading.w + 180
		})
		// How far this course's stars go. The skin has this pre-drawn per
		// course; ours reads it off the library, so it is written out.
		ctx.save()
		ctx.globalAlpha = fade
		this.label(ctx, "\u26051 \uFF5E \u2605" + this.limits[this.selectedBox], {
			x: this.frameLeft + P.limit.x + size.limit.w / 2,
			y: this.frameTop + P.limit.y + size.limit.h / 2,
			size: 34,
			width: size.limit.w
		})
		ctx.restore()

		this.tex(ctx, "level_box", {fade: fade})
		// The course's emblem and its name, where the skin drew both
		// together in one Japanese image.
		this.tex(ctx, "stat_diff", {
			frame: this.selectedBox, frames: 5, fade: fade,
			x: P.diff.x - P.stat_diff.x - 4,
			y: P.diff.y - P.stat_diff.y - 8
		})
		ctx.save()
		ctx.globalAlpha = fade
		this.label(ctx, this.boxLabel(this.selectedBox), {
			x: this.frameLeft + P.diff.x + size.emblem + 96,
			y: this.frameTop + P.diff.y + size.diff.h / 2,
			size: 40,
			width: 190
		})
		ctx.restore()

		this.drawLevelNumber(ctx, fade)
		var spacing = this.starSpacing()
		for(var i = 0; i < this.selectedLevel; i++){
			this.tex(ctx, "star", {x: i * spacing, fade: fade})
		}

		if(this.confirmation){
			// The prompt darkens the level box behind it rather than
			// replacing it, so what is being confirmed stays readable.
			var box = DiffSortSelect.pos.level_box
			ctx.fillStyle = "rgba(0, 0, 0, 0.5)"
			ctx.fillRect(this.frameLeft + box.x, this.frameTop + box.y,
				size.levelBox.w, size.levelBox.h)

			var y = this.bounce(ms)
			var offset = DiffSortSelect.smallBoxOffset
			var flicker = this.flicker(ms)
			var prompts = [strings.diffSort.changeStars, strings.diffSort.ok,
				strings.diffSort.changeDifficulty]
			for(var i = 0; i < 3; i++){
				var on = i === this.confirmIndex
				this.tex(ctx, on ? "small_box_highlight" : "small_box", {x: i * offset, y: y})
				this.label(ctx, prompts[i], {
					x: this.frameLeft + P.small_box.x + i * offset + size.smallBox.w / 2,
					y: this.frameTop + P.small_box.y + y + size.smallBox.h / 2,
					size: i === 1 ? 40 : 26,
					width: size.smallBox.w - 26,
					outline: on ? "#8a4b12" : "#000"
				})
				if(on){
					this.tex(ctx, "small_box_outline", {x: i * offset, y: y, fade: flicker})
				}
			}
		}else{
			this.tex(ctx, "pongos")
			var drift = this.arrowPulse(ms) * DiffSortSelect.anim.arrow.distance
			var arrowFade = this.arrowPulse(ms)
			if(this.selectedLevel !== 1){
				this.tex(ctx, "arrow", {index: 0, x: -drift, fade: arrowFade})
			}
			if(this.selectedLevel !== this.limits[this.selectedBox]){
				this.tex(ctx, "arrow", {index: 1, mirror: true, x: drift, fade: arrowFade})
			}
		}
		this.drawStatistics(ctx)
	}

	draw(ctx, frameLeft, frameTop, winW, winH, ms){
		this.frameLeft = frameLeft
		this.frameTop = frameTop
		// Over everything, the wheel included. YataiDON dims the whole
		// screen rather than only the area the panel covers.
		ctx.fillStyle = "rgba(0, 0, 0, 0.6)"
		ctx.fillRect(0, 0, winW, winH)
		if(this.inLevelSelect){
			this.drawLevelSelect(ctx, ms)
		}else{
			this.drawDiffSelect(ctx, ms)
		}
	}
}
