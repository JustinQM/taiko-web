/*
 * Owns what is in the song wheel.
 *
 * SongSelect used to build one flat array of every song in init() and
 * index into it for the rest of its life. That array is about to become
 * the listing of whichever folder you are standing in, so the building of
 * it moves here first, unchanged, before anything about it changes.
 *
 * The renderer never learns there is a tree: a folder listing is a flat
 * array too, and descending swaps the array and resets the index.
 */
class SongNavigator{
	// A way out every this many songs, as YataiDON does. One back box at
	// the top of a folder of several hundred is not a way out.
	static backEvery = 10
	
	// The difficulty search's courses, in the order its boxes are drawn.
	//
	// YataiDON stops each course at a fixed star -- 5, 7, 8, 10, 10 --
	// because its star_limit artwork is five pre-drawn strips saying so.
	// Ours draws that line as text, so the cap can come from the library
	// instead, and every chart in it is reachable. The ceiling below is
	// only a guard against a .tja claiming something absurd; nothing in
	// the library comes near it.
	static diffSortCourses = ["easy", "normal", "hard", "oni", "ura"]
	static diffSortCeiling = 20
	
	constructor(...args){
		this.init(...args)
	}
	init(config){
		this.config = config
		// Where in the tree we are: the folders descended into, outermost
		// first. Empty is the root.
		this.path = []
		// One entry per level above the current one, holding the listing
		// and the cursor to put back when we come up.
		this.stack = []
		// Where the cursor was last left inside each folder, so reopening
		// one returns to the song you were on rather than to the top.
		// YataiDON keeps reopen_folder_path and reopen_song_path for this
		// and it matters more in use than it sounds.
		this.lastIndex = {}
		// What the difficulty search folder is currently showing. Null
		// until the picker has been through once.
		this.diffSort = null
		this.songItems = this.buildSongs()
		this.items = this.buildRoot()
	}
	
	/*
	 * Every song as a wheel entry, sorted into category runs. Built once:
	 * the folder listings are windows onto this, not rebuilds of it.
	 */
	buildSongs(){
		var skin = this.config.skin
		var songs = []
		for(let song of this.config.songs){
			this.config.updateSearchText(song)
			songs.push(this.config.addSong(song))
		}
		// addSong copies every property of the song onto the wheel entry,
		// and a folder entry keeps its folder on .folder. Move the song's
		// source path out of the way so the two cannot be confused.
		songs.forEach(song => {
			song.folderPath = Array.isArray(song.folder) ? song.folder : null
			delete song.folder
		})
		songs.sort((a, b) => {
			var catA = a.originalCategory in skin ? skin[a.originalCategory] : skin.default
			var catB = b.originalCategory in skin ? skin[b.originalCategory] : skin.default
			if(catA.sort !== catB.sort){
				return catA.sort > catB.sort ? 1 : -1
			}else if(a.originalCategory !== b.originalCategory){
				return a.originalCategory > b.originalCategory ? 1 : -1
			}else if(a.order !== b.order){
				return a.order > b.order ? 1 : -1
			}else{
				return a.id > b.id ? 1 : -1
			}
		})
		return songs
	}
	
	/*
	 * The genre folders, in the order the songs are already sorted into,
	 * so the wheel's category order is unchanged -- it has just gone from
	 * runs within one list to folders.
	 */
	buildGenreFolders(){
		var skin = this.config.skin
		var folders = []
		var byCategory = {}
		for(let song of this.songItems){
			var key = song.originalCategory
			if(!(key in byCategory)){
				byCategory[key] = {
					id: "genre:" + key,
					title: song.category,
					originalCategory: key,
					skin: key in skin ? skin[key] : skin.default,
					songs: []
				}
				folders.push(byCategory[key])
			}
			byCategory[key].songs.push(song)
		}
		folders.forEach(folder => this.nest(folder, 0))
		return folders.map(folder => this.folderItem(folder))
	}
	
	folderItem(folder){
		return {
			title: folder.title,
			category: folder.title,
			originalCategory: folder.originalCategory,
			skin: folder.skin,
			action: "folder",
			folder: folder,
			canJump: true
		}
	}
	
	/*
	 * Split a folder's songs into sub-folders by the next component of
	 * their source path, recursively.
	 *
	 * Most songs have no path left once the pack and the genre are
	 * accounted for, so most genres stay flat and this does nothing. The
	 * ones that do -- the OpenTaiko collaborations -- get the structure
	 * they had on disk. A database imported before the field existed has
	 * none of it and lists everything flat, which is why this is driven
	 * off the songs rather than off a separate tree.
	 */
	nest(folder, depth){
		var groups = {}
		var order = []
		var here = []
		folder.songs.forEach(song => {
			var path = song.folderPath
			if(!path || path.length <= depth){
				here.push(song)
				return
			}
			var name = path[depth]
			if(!(name in groups)){
				groups[name] = {
					id: folder.id + "/" + name,
					title: name,
					originalCategory: folder.originalCategory,
					skin: folder.skin,
					songs: []
				}
				order.push(groups[name])
			}
			groups[name].songs.push(song)
		})
		if(!order.length){
			return
		}
		order.forEach(child => this.nest(child, depth + 1))
		folder.children = order
		folder.songs = here
	}
	
	/*
	 * A random song from the whole library, and the way to it.
	 *
	 * Random used to pick from the current listing, which at the root now
	 * holds no songs at all -- the loop looking for one there never
	 * terminated. Picking from every song and then opening the folder it
	 * lives in is also what the entry means: random across the library,
	 * not random within where you happen to be standing.
	 */
	randomSong(){
		if(!this.songItems.length){
			return null
		}
		var song = this.songItems[Math.floor(Math.random() * this.songItems.length)]
		return this.locate(song)
	}
	
	/*
	 * Find the way to a song: the folder path to open, and where it sits
	 * in that folder's listing. Walks the whole tree, because a song can
	 * be nested below its genre.
	 */
	locate(song){
		var found = null
		var walk = (folder, path) => {
			if(found){
				return
			}
			if(folder.songs.indexOf(song) !== -1){
				// Ask the listing rather than working the offset out:
				// back boxes are interleaved through it, so counting by
				// hand would drift.
				found = {
					path: path,
					index: this.buildFolder(folder).indexOf(song)
				}
				return
			}
			;(folder.children || []).forEach(child =>
				walk(child, path.concat([child.id])))
		}
		this.rootItems().forEach(item => {
			if(this.isFolder(item) && item.folder.id.indexOf("genre:") === 0){
				walk(item.folder, [item.folder.id])
			}
		})
		return found
	}
	
	/*
	 * Open a folder path and return where the cursor should land in it.
	 */
	jumpToPath(path, index){
		if(!this.goToPath(path)){
			return null
		}
		return Math.min(Math.max(0, index), this.items.length - 1)
	}
	
	/*
	 * Where we are, as something that survives the wire. Folder ids rather
	 * than indices, because an index only means anything against a listing
	 * the other side may not have open.
	 */
	pathIds(){
		return this.path.map(folder => folder.id)
	}
	
	/*
	 * Put the navigator at a path described by pathIds. Returns true if it
	 * ended up there, false if the path named a folder that does not
	 * exist, in which case it is left at the root.
	 */
	goToPath(ids){
		while(this.stack.length){
			this.back(0)
		}
		for(var i = 0; i < ids.length; i++){
			var index = this.items.findIndex(item =>
				item.folder && item.folder.id === ids[i])
			if(index === -1){
				while(this.stack.length){
					this.back(0)
				}
				return false
			}
			this.enter(index)
		}
		return true
	}
	
	samePath(ids){
		var here = this.pathIds()
		return here.length === ids.length && here.every((id, i) => id === ids[i])
	}
	
	rootItems(){
		return this.stack.length ? this.stack[0].items : this.items
	}
	
	/*
	 * A folder whose contents are worked out when it is opened rather than
	 * fixed when the wheel is built, so it reflects whatever has been
	 * favorited since. YataiDON declares these in box.def with
	 * #COLLECTION and resolves them the same way.
	 */
	collectionFolder(spec){
		var folder = {
			id: spec.id,
			title: spec.title,
			originalCategory: spec.originalCategory || spec.title,
			collection: spec.songs,
			songs: []
		}
		return {
			title: spec.title,
			category: spec.title,
			originalCategory: folder.originalCategory,
			skin: spec.skin,
			// Drawn as a slat rather than a folder block, and opened like
			// one all the same. A genre folder is a division of the
			// library and earns the width; these are ways of picking a
			// song out of it, and belong with Random and Search. The
			// wheel decides that on the action alone, so it is enough to
			// carry the folder without being called one.
			action: "collection",
			folder: folder
		}
	}
	
	/*
	 * Resolve a SongList to wheel entries, keeping its order -- newest
	 * first, which is how both the server and the local copy store them.
	 * A song that has since gone from the library is dropped rather than
	 * leaving a hole.
	 */
	listSongs(list){
		if(!list){
			return []
		}
		return list.songs
			.map(id => this.songItems.find(song => song.id === id))
			.filter(Boolean)
	}
	
	favoriteSongs(){
		return this.listSongs(typeof favorites !== "undefined" && favorites)
	}
	
	/*
	 * Every chart at one course and one star level, across the whole
	 * library rather than within a genre.
	 *
	 * YataiDON walks each sibling genre folder and keeps the songs whose
	 * course_data has that course at exactly that level. Exactly: a
	 * ten-star search is ten-star charts, not ten and above. Ours is the
	 * same test over the flat song list, which is the same set.
	 */
	diffSortSongs(course, level){
		var name = SongNavigator.diffSortCourses[course]
		if(!name){
			return []
		}
		return this.songItems.filter(song =>
			song.courses && song.courses[name] && song.courses[name].stars === level)
	}
	
	/*
	 * How many charts there are at each course and level, how many are
	 * cleared and how many are full combos -- the panel down the left of
	 * the picker.
	 *
	 * YataiDON parses every .tja on the disk for this and does it on a
	 * background thread while song select loads. Ours is one pass over a
	 * list already in memory, so the picker just asks for it when it
	 * opens and holds on to what it gets -- no cache to go stale behind
	 * a login finishing or a peer's crowns arriving.
	 */
	diffSortStats(){
		var courses = SongNavigator.diffSortCourses
		var ceiling = SongNavigator.diffSortCeiling
		var stats = courses.map(() => {
			var levels = []
			for(var i = 0; i <= ceiling; i++){
				levels.push({total: 0, clears: 0, fullCombos: 0, donderfuls: 0})
			}
			return levels
		})
		var haveScores = typeof scoreStorage !== "undefined"
		this.songItems.forEach(song => {
			if(!song.courses){
				return
			}
			var score = haveScores ? scoreStorage.scores[song.hash] : null
			for(var course = 0; course < courses.length; course++){
				var chart = song.courses[courses[course]]
				if(!chart){
					continue
				}
				var level = chart.stars
				if(!(level >= 1) || level > ceiling){
					continue
				}
				var cell = stats[course][level]
				cell.total++
				var crown = score && score[courses[course]] && score[courses[course]].crown
				if(!crown){
					continue
				}
				// Cumulative, and deliberately so: a crown counts in its
				// own row and in every row above it, because a full combo
				// is a clear and a donderful is both. YataiDON counts its
				// two rows this way and the leaderboard now does too.
				cell.clears++
				if(crown !== "silver"){
					cell.fullCombos++
				}
				if(crown === "rainbow"){
					cell.donderfuls++
				}
			}
		})
		return stats
	}
	
	/*
	 * The highest star level each course actually has a chart at, which
	 * is how far its half of the picker goes.
	 *
	 * A course with nothing in it at all still offers one star rather
	 * than none, so the screen has something to stand on.
	 */
	diffSortLimits(stats){
		stats = stats || this.diffSortStats()
		return stats.map(levels => {
			for(var level = levels.length - 1; level >= 1; level--){
				if(levels[level].total){
					return level
				}
			}
			return 1
		})
	}
	
	folderId(item){
		return item.folder ? item.folder.id : null
	}
	
	isFolder(item){
		return !!item && item.action === "folder"
	}
	
	isBack(item){
		return !!item && item.action === "back"
	}
	
	/*
	 * Descend. The listing and cursor of the level being left are pushed so
	 * back() can restore them exactly.
	 */
	enter(index){
		var item = this.items[index]
		// Carrying a folder rather than being drawn as one: the
		// difficulty search is a slim entry and still descends.
		if(!item || !item.folder){
			return null
		}
		this.stack.push({
			items: this.items,
			index: index,
			path: this.path.slice()
		})
		this.path.push(item.folder)
		this.items = this.buildFolder(item.folder)
		// Back to wherever the cursor was left in here before, if we have
		// been in before; otherwise the first song rather than the back box.
		var remembered = this.lastIndex[item.folder.id]
		return remembered !== undefined && remembered < this.items.length ? remembered : 1
	}
	
	/*
	 * Ascend, restoring the listing and the cursor of the level above.
	 * Remembers where the cursor was, so coming back in returns to it.
	 */
	back(currentIndex){
		if(!this.stack.length){
			return null
		}
		var folder = this.path[this.path.length - 1]
		if(folder){
			this.lastIndex[folder.id] = currentIndex
		}
		var previous = this.stack.pop()
		this.path = previous.path
		this.items = previous.items
		return previous.index
	}
	
	/*
	 * A folder's listing: a back box, then its songs.
	 */
	backItem(folder){
		return {
			title: strings.back,
			category: folder.title,
			originalCategory: folder.originalCategory,
			skin: this.config.skin.back,
			action: "back"
		}
	}
	
	/*
	 * A folder's listing: a back box, its sub-folders, then its songs with
	 * another back box every backEvery of them.
	 *
	 * The repeats are YataiDON's, and they are what make a folder of
	 * several hundred songs usable: with one back box at the top, leaving
	 * a genre means scrolling all the way back to it. Sub-folders come
	 * before songs, as they sort on disk.
	 */
	buildFolder(folder){
		if(folder.collection){
			folder.songs = folder.collection()
		}
		var items = [this.backItem(folder)]
		if(folder.children){
			items = items.concat(folder.children.map(child => this.folderItem(child)))
		}
		folder.songs.forEach((song, i) => {
			if(i > 0 && i % SongNavigator.backEvery === 0){
				items.push(this.backItem(folder))
			}
			items.push(song)
		})
		return items
	}
	
	/*
	 * The root listing, ordered as YataiDON orders its own: the genres
	 * first, then its collection folders, then -- ours only -- taiko-web's
	 * menu entries, which it has no equivalent for.
	 *
	 * YataiDON drives the order from numeric directory-name prefixes:
	 * genres 01 to 09, then 11 Dan Dojo, 13 Recommended, 14 Favorites,
	 * 15 Recently Played, 16 Difficulty Sort, 17 New, 18 Search. Dan Dojo
	 * and Recommended are left out: we have no dan mode, and nothing here
	 * can base a recommendation on anything.
	 *
	 * Difficulty Sort was left out too, on the grounds that the search
	 * box already takes an "oni:9" filter. Browsing by course and level
	 * is not that: it is a screen that tells you how many ten-star Oni
	 * charts there are and how many of them you have cleared, and then
	 * puts them in the wheel. It goes after Search rather than before
	 * Random, which is where YataiDON has it -- the three ways of finding
	 * a song that is not in front of you read better together.
	 */
	buildRoot(){
		var config = this.config
		var skin = config.skin
		var items = this.buildGenreFolders()
		
		if(config.songs.length){
			items.push(this.collectionFolder({
				id: "collection:favorites",
				title: strings.favorites.title,
				skin: skin.favorites || skin.random,
				songs: () => this.favoriteSongs()
			}))
			items.push(this.collectionFolder({
				id: "collection:recent",
				title: strings.recentlyPlayed.title,
				skin: skin.recent || skin.tutorial,
				songs: () => this.listSongs(typeof recentlyPlayed !== "undefined" && recentlyPlayed)
			}))
			items.push({
				title: strings.randomSong,
				skin: skin.random,
				action: "random",
				category: strings.randomSong,
				canJump: true
			})
			items.push({
				title: strings.search.search,
				skin: skin.search,
				action: "search",
				category: strings.search.search
			})
			// Opening this does not list anything: the picker comes up
			// first and what it chooses is what the folder then holds.
			// SongSelect intercepts it, the way YataiDON's navigator
			// stops on #COLLECTION:DIFFICULTY and waits.
			//
			// So it is drawn as a slim entry rather than as a folder
			// box, next to Random and Search. It is one of the ways of
			// finding a song you cannot see, which is what those are;
			// a folder box promises a listing behind it, and there is
			// none until the picker has been answered. It still carries
			// a folder for the answer to fill.
			var diffSort = this.collectionFolder({
				id: "collection:diffsort",
				title: strings.diffSort.title,
				skin: skin.diffSort,
				songs: () => this.diffSort
					? this.diffSortSongs(this.diffSort.course, this.diffSort.level)
					: []
			})
			diffSort.action = "diffSort"
			items.push(diffSort)
		}
		// How to Play and About are read once and never again, and at the
		// root every entry costs a press to scroll past. Both are still
		// reachable -- the tutorial from a fresh profile, About from the
		// version link -- they are just not in the way any more.
		items.push({
			title: strings.gameSettings,
			skin: skin.settings,
			action: "settings",
			category: strings.gameSettings
		})
		if(plugins.hasSettings()){
			items.push({
				title: strings.plugins.title,
				skin: skin.plugins,
				action: "plugins",
				category: strings.plugins.title
			})
		}
		return items
	}
}
