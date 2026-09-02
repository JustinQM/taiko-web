/*
 * A named per-user list of songs.
 *
 * Two exist: favourites, which the player adds to deliberately, and
 * recently played, which is written on every play and trimmed by the
 * server. They are the same thing with a different slug, and a
 * user-created playlist later would be a third with a name attached.
 *
 * Mirrors scoreStorage: the server holds them when someone is signed in
 * and localStorage when they are not, with no merging between the two --
 * signing in shows the account's list, signing out shows the browser's
 * again.
 */
class SongList{
	constructor(...args){
		this.init(...args)
	}
	init(slug, limit){
		this.slug = slug
		this.limit = limit || 0
		this.songs = []
		this.loaded = false
		// Deliberately not loaded here: this is constructed before the
		// account has resolved, so it would always read localStorage and
		// then never look at the server. The loader calls load() once it
		// knows, and account.js calls it again on sign in and sign out.
	}
	
	localKey(){
		return "songlist:" + this.slug
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
		return this.set(songId, !this.has(songId))
	}
	
	/*
	 * Put a song in the list or take it out. Adding something already
	 * there moves it to the front rather than duplicating it, which is
	 * what recently played needs.
	 */
	set(songId, add){
		if(this.has(songId)){
			this.songs.splice(this.songs.indexOf(songId), 1)
		}
		if(add){
			this.songs.unshift(songId)
			if(this.limit){
				this.songs.splice(this.limit)
			}
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
	
	/*
	 * Writes are chained rather than fired in parallel.
	 *
	 * Each one fetches a CSRF token first, so two toggles in quick
	 * succession can reach the server in the opposite order to the one
	 * they were made in and the list ends up disagreeing with the screen.
	 * Queueing them keeps the server's order the player's order.
	 */
	post(songId, value){
		this.queue = (this.queue || Promise.resolve())
			.catch(() => {})
			.then(() => this.send(songId, value))
		return this.queue
	}
	
	send(songId, value){
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
