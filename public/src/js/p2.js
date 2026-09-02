class P2Connection{
	constructor(...args){
		this.init(...args)
	}
	init(){
		this.closed = true
		this.lastMessages = {}
		this.otherConnected = false
		this.name = null
		this.player = 1
		this.allEvents = new Map()
		this.addEventListener("message", this.message.bind(this))
		// Nothing closed the socket when the page went away, so a refresh
		// left the server holding the connection until it noticed --
		// which on a matchmaking server means ghosts in the waiting list.
		// pagehide is the one that fires on mobile, where beforeunload
		// often does not.
		this.unloadHandler = () => this.close()
		pageEvents.add(window, "beforeunload", this.unloadHandler, Symbol())
		pageEvents.add(window, "pagehide", this.unloadHandler, Symbol())
		this.currentHash = ""
		this.disabled = 0
		pageEvents.add(window, "hashchange", this.onhashchange.bind(this))
	}
	addEventListener(type, callback){
		var addedType = this.allEvents.get(type)
		if(!addedType){
			addedType = new Set()
			this.allEvents.set(type, addedType)
		}
		return addedType.add(callback)
	}
	removeEventListener(type, callback){
		var addedType = this.allEvents.get(type)
		if(addedType){
			return addedType.delete(callback)
		}
	}
	open(){
		if(this.closed && !this.disabled){
			this.closed = false
			var wsProtocol = location.protocol == "https:" ? "wss:" : "ws:"
			this.socket = new WebSocket(wsProtocol + "//" + location.host + "/p2")
			// Listened for separately rather than through race, which
			// removes both listeners as soon as either fires: once a
			// connection succeeded the close listener was gone, so a
			// disconnect after that point was never noticed and the retry
			// below was unreachable in the case it was written for.
			pageEvents.add(this.socket, "open", () => this.openEvent(), Symbol())
			pageEvents.add(this.socket, "close", () => this.closeEvent(), Symbol())
			pageEvents.add(this.socket, "message", this.messageEvent.bind(this))
		}
	}
	openEvent(){
		// A connection that lasted means the next failure starts over
		// from a short wait rather than the long one it had backed off to.
		this.retryDelay = 0
		var addedType = this.allEvents.get("open")
		if(addedType){
			addedType.forEach(callback => callback())
		}
	}
	close(){
		if(!this.closed){
			this.closed = true
			if(this.retryTimeout){
				clearTimeout(this.retryTimeout)
				this.retryTimeout = null
			}
			if(this.socket){
				this.socket.close()
			}
		}
	}
	closeEvent(){
		// This used to open with removeEventListener(onmessage), and
		// 'onmessage' is not defined anywhere -- had this ever been
		// reached it would have thrown before getting to the retry.
		this.otherConnected = false
		this.session = false
		if(this.hashLock){
			this.hash("")
			this.hashLock = false
		}
		if(!this.closed){
			// Backed off rather than a flat half second, so a server that
			// is down is not asked once a second forever. Reset by a
			// connection that lasts.
			this.retryDelay = Math.min(8000, (this.retryDelay || 0) * 2 || 500)
			this.retryTimeout = setTimeout(() => {
				this.retryTimeout = null
				if(!this.socket || this.socket.readyState !== this.socket.OPEN){
					// closed is still false here, and open() only acts when
					// it is true, so it is flipped for the retry itself.
					this.closed = true
					this.open()
				}
			}, this.retryDelay)
			pageEvents.send("p2-disconnected")
		}
		var addedType = this.allEvents.get("close")
		if(addedType){
			addedType.forEach(callback => callback())
		}
	}
	send(type, value){
		if(this.socket.readyState === this.socket.OPEN){
			if(typeof value === "undefined"){
				this.socket.send(JSON.stringify({type: type}))
			}else{
				this.socket.send(JSON.stringify({type: type, value: value}))
			}
		}else{
			pageEvents.once(this, "open").then(() => {
				this.send(type, value)
			})
		}
	}
	messageEvent(event){
		try{
			var response = JSON.parse(event.data)
		}catch(e){
			var response = {}
		}
		this.lastMessages[response.type] = response
		var addedType = this.allEvents.get("message")
		if(addedType){
			addedType.forEach(callback => callback(response))
		}
	}
	getMessage(type){
		if(type in this.lastMessages){
			return this.lastMessages[type]
		}
	}
	clearMessage(type){
		if(type in this.lastMessages){
			this.lastMessages[type] = null
		}
	}
	message(response){
		switch(response.type){
			case "gameload":
				if("player" in response.value){
					this.player = response.value.player === 2 ? 2 : 1
				}
			case "gamestart":
				this.otherConnected = true
				this.notes = []
				this.drumrollPace = 45
				this.dai = 2
				this.kaAmount = 0
				this.results = false
				this.branch = "normal"
				scoreStorage.clearP2()
				break
			case "gameend":
				this.otherConnected = false
				if(this.session){
					pageEvents.send("session-end")
				}else if(!this.results){
					pageEvents.send("p2-game-end")
				}
				this.session = false
				if(this.hashLock){
					this.hash("")
					this.hashLock = false
				}
				this.name = null
				this.don = null
				scoreStorage.clearP2()
				break
			case "gameresults":
				this.results = {}
				for(var i in response.value){
					this.results[i] = response.value[i] === null ? null : response.value[i].toString()
				}
				break
			case "note":
				this.notes.push(response.value)
				if(response.value.dai){
					this.dai = response.value.dai
				}
				break
			case "drumroll":
				this.drumrollPace = response.value.pace
				if("kaAmount" in response.value){
					this.kaAmount = response.value.kaAmount
				}
				break
			case "branch":
				this.branch = response.value
				this.branchSet = false
				break
			case "session":
				this.clearMessage("users")
				this.otherConnected = true
				this.session = true
				scoreStorage.clearP2()
				if("player" in response.value){
					this.player = response.value.player === 2 ? 2 : 1
				}
				break
			case "name":
				this.name = response.value ? (response.value.name || "").toString() : ""
				this.don = response.value ? (response.value.don) : null
				break
			case "getcrowns":
				if(response.value){
					var output = {}
					for(var i in response.value){
						if(response.value[i]){
							var score = scoreStorage.get(response.value[i], false, true)
							if(score){
								var crowns = {}
								for(var diff in score){
									if(diff !== "title"){
										crowns[diff] = {
											crown: score[diff].crown
										}
									}
								}
							}else{
								var crowns = null
							}
							output[response.value[i]] = crowns
						}
					}
					p2.send("crowns", output)
				}
				break
			case "crowns":
				if(response.value){
					for(var i in response.value){
						scoreStorage.addP2(i, false, response.value[i], true)
					}
				}
				break
		}
	}
	onhashchange(){
		if(this.hashLock){
			this.hash(this.currentHash)
		}else{
			location.reload()
		}
	}
	hash(string){
		this.currentHash = string
		history.replaceState("", "", location.pathname + (string ? "#" + string : ""))
	}
	play(circle, mekadon){
		if(this.otherConnected || this.notes.length > 0){
			var type = circle.type
			var drumrollNotes = type === "balloon" || type === "drumroll" || type === "daiDrumroll"
			
			if(drumrollNotes && mekadon.getMS() > circle.endTime + mekadon.delay){
				circle.played(-1, false)
				mekadon.game.updateCurrentCircle()
			}
			
			if(drumrollNotes){
				mekadon.playDrumrollAt(circle, 0, this.drumrollPace, type === "drumroll" || type === "daiDrumroll" ? this.kaAmount : 0)
			}else if(this.notes.length === 0){
				mekadon.play(circle)
			}else{
				var note = this.notes[0]
				if(note.score >= 0){
					var dai = 1
					if(circle.type === "daiDon" || circle.type === "daiKa"){
						dai = this.dai
					}
					if(mekadon.playAt(circle, note.ms, note.score, dai, note.reverse)){
						this.notes.shift()
					}
				}else{
					if(mekadon.miss(circle)){
						this.notes.shift()
					}
				}
			}
		}else if(mekadon.miss(circle)){
			this.notes.shift()
		}
	}
	enable(){
		this.disabled = Math.max(0, this.disabled - 1)
		setTimeout(this.open.bind(this), 100)
	}
	disable(){
		this.disabled++
		this.close()
	}
}
