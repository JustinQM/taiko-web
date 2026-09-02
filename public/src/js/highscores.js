/*
 * The leaderboard, as the game sees it.
 *
 * The service and its API are unchanged -- /highscores/api/song/<id>
 * returns a board per difficulty -- and the website is still the place to
 * go for anything more than the top few names. This is only about the
 * game drawing them itself rather than a panel sitting over the top of
 * it in a different design.
 *
 * Everything degrades to nothing: no service, no network, no scores for
 * this song all end up drawing an empty board rather than an error.
 */
class Highscores{
	constructor(...args){
		this.init(...args)
	}
	init(){
		this.cache = {}
		this.pending = {}
	}
	
	/*
	 * The boards for a song, or null while they are still on their way.
	 * Asking twice for the same song does not fetch twice.
	 */
	get(songId){
		if(!songId && songId !== 0){
			return null
		}
		if(songId in this.cache){
			return this.cache[songId]
		}
		if(!(songId in this.pending)){
			this.pending[songId] = true
			this.fetch(songId)
		}
		return null
	}
	
	fetch(songId){
		var request = new XMLHttpRequest()
		request.open("GET", "/highscores/api/song/" + songId)
		pageEvents.load(request).then(() => {
			var boards = null
			if(request.status === 200){
				try{
					boards = JSON.parse(request.response).boards || null
				}catch(e){}
			}
			// A failure caches as "nothing to show" rather than retrying on
			// every frame the difficulty screen is open.
			this.cache[songId] = boards
			delete this.pending[songId]
		}).catch(() => {
			this.cache[songId] = null
			delete this.pending[songId]
		})
		request.send()
	}
	
	/*
	 * The board for one difficulty, with its rows already ordered by rank.
	 */
	board(songId, difficulty){
		var boards = this.get(songId)
		if(!boards || !(difficulty in boards)){
			return null
		}
		return boards[difficulty]
	}
	
	url(songId){
		return "/highscores/song/" + songId
	}
}
