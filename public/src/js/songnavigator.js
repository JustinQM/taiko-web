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
		// Where in the tree we are. Empty is the root, and for now it is
		// the only listing there is.
		this.path = []
		this.items = this.buildRoot()
	}
	
	/*
	 * The root listing: every song, sorted into category runs, then the
	 * menu entries. This is a straight lift of what SongSelect.init() did
	 * and produces the same array in the same order.
	 */
	buildRoot(){
		var config = this.config
		var skin = config.skin
		var items = []
		
		for(let song of config.songs){
			config.updateSearchText(song)
			items.push(config.addSong(song))
		}
		items.sort((a, b) => {
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
		if(config.showCustomSongs){
			items.push({
				title: assets.customSongs ? strings.customSongs.default : strings.customSongs.title,
				skin: skin.customSongs,
				action: "customSongs",
				category: assets.customSongs ? strings.customSongs.default : strings.customSongs.title
			})
		}
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
