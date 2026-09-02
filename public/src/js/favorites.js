/*
 * Per-user song lists, and the favourites list in particular.
 *
 * Mirrors scoreStorage: the server holds them when someone is logged in
 * and localStorage does when they are not, with no merging between the
 * two -- signing in shows the account's list, signing out shows the
 * browser's again.
 *
 * The server stores these as playlists keyed by a slug, so user-created
 * lists later are more rows and a screen rather than a migration. Only
 * favourites has a way into it today.
 */
class Favorites{
	constructor(...args){
		this.init(...args)
	}
	init(){
		this.slug = "favorites"
		this.songs = []
		this.loaded = false
		// Deliberately not loaded here: this is constructed before the
		// account has resolved, so it would always read localStorage and
		// then never look at the server. The loader calls load() once it
		// knows, and account.js calls it again on sign in and sign out.
	}
	
	localKey(){
		return "favorites"
	}
	
	loggedIn(){
		return !!(account && account.loggedIn)
	}
	
	load(){
		if(this.loggedIn()){
			return loader.ajax("api/playlists/" + this.slug).then(response => {
				var data = JSON.parse(response)
				this.songs = data.status === "ok" && Array.isArray(data.songs) ? data.songs : []
				this.loaded = true
			}).catch(() => {
				this.songs = []
				this.loaded = true
			})
		}
		try{
			var stored = JSON.parse(localStorage.getItem(this.localKey()) || "[]")
			this.songs = Array.isArray(stored) ? stored.filter(id => typeof id === "number") : []
		}catch(e){
			this.songs = []
		}
		this.loaded = true
		return Promise.resolve()
	}
	
	has(songId){
		return this.songs.indexOf(songId) !== -1
	}
	
	/*
	 * Flip a song's membership. The new state is applied locally straight
	 * away so the wheel can redraw on the same frame, and sent with an
	 * explicit value so a retry cannot toggle it twice.
	 */
	toggle(songId){
		var add = !this.has(songId)
		if(add){
			this.songs.unshift(songId)
		}else{
			this.songs.splice(this.songs.indexOf(songId), 1)
		}
		
		if(this.loggedIn()){
			this.post(songId, add)
		}else{
			try{
				localStorage.setItem(this.localKey(), JSON.stringify(this.songs))
			}catch(e){}
		}
		return add
	}
	
	post(songId, value){
		// Same shape as scoreStorage's save: fetch a CSRF token, then send.
		return loader.getCsrfToken().then(token => {
			var request = new XMLHttpRequest()
			request.open("POST", "api/playlists")
			var promise = pageEvents.load(request)
			request.setRequestHeader("Content-Type", "application/json")
			request.setRequestHeader("X-CSRFToken", token)
			request.send(JSON.stringify({
				slug: this.slug,
				song_id: songId,
				value: value
			}))
			return promise
		}).catch(() => {})
	}
	
	clear(){
		this.songs = []
	}
}
