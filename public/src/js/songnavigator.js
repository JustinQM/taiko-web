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
		return folders.map(folder => ({
			title: folder.title,
			category: folder.title,
			originalCategory: folder.originalCategory,
			skin: folder.skin,
			action: "folder",
			folder: folder,
			canJump: true
		}))
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
		var rootIndex = this.rootItems().findIndex(item =>
			this.isFolder(item) && item.folder.songs.indexOf(song) !== -1)
		if(rootIndex === -1){
			return null
		}
		var folderItem = this.rootItems()[rootIndex]
		return {
			rootIndex: rootIndex,
			folder: folderItem.folder,
			// +1 for the back box the folder listing starts with
			index: folderItem.folder.songs.indexOf(song) + 1
		}
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
				this.isFolder(item) && item.folder.id === ids[i])
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
	 * Jump straight to a folder and a position inside it, from wherever we
	 * are. Used by random, and by anything else that knows where it wants
	 * to land rather than how to walk there.
	 */
	jumpTo(rootIndex, index){
		while(this.stack.length){
			this.back(0)
		}
		this.enter(rootIndex)
		return Math.min(Math.max(0, index), this.items.length - 1)
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
		if(!this.isFolder(item)){
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
	buildFolder(folder){
		var items = [{
			title: strings.back,
			category: folder.title,
			originalCategory: folder.originalCategory,
			skin: this.config.skin.back,
			action: "back"
		}]
		return items.concat(folder.songs)
	}
	
	/*
	 * The root listing, ordered as YataiDON orders its own: the genres
	 * first, then its collection folders, then -- ours only -- taiko-web's
	 * menu entries, which it has no equivalent for.
	 *
	 * YataiDON drives the order from numeric directory-name prefixes:
	 * genres 01 to 09, then 11 Dan Dojo, 13 Recommended, 14 Favorites,
	 * 15 Recently Played, 16 Difficulty Sort, 17 New, 18 Search. Dan Dojo,
	 * Difficulty Sort and Recommended are left out: we have no dan mode,
	 * search already filters by difficulty, and nothing here can base a
	 * recommendation on anything.
	 */
	buildRoot(){
		var config = this.config
		var skin = config.skin
		var items = this.buildGenreFolders()
		
		if(config.songs.length){
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
		}
		if(config.showTutorial){
			items.push({
				title: strings.howToPlay,
				skin: skin.tutorial,
				action: "tutorial",
				category: strings.howToPlay
			})
		}
		items.push({
			title: strings.aboutSimulator,
			skin: skin.about,
			action: "about",
			category: strings.aboutSimulator
		})
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
