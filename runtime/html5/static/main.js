/**
 * Copyright FunASR (https://github.com/alibaba-damo-academy/FunASR). All Rights
 * Reserved. MIT License  (https://opensource.org/licenses/MIT)
 */
/* 2022-2023 by zhaoming,mali aihealthx.com */


// 连接; 定义socket连接类对象与语音对象
var wsconnecter = new WebSocketConnectMethod({msgHandle:getJsonMessage,stateHandle:getConnState});
var audioBlob;

// 录音; 定义录音对象,wav格式
var rec = Recorder({
	type:"pcm",
	bitRate:16,
	sampleRate:16000,
	onProcess:recProcess
});

 
 
 
var sampleBuf=new Int16Array();
// 定义按钮响应事件
var btnStart = document.getElementById('btnStart');
btnStart.onclick = record;
var btnStop = document.getElementById('btnStop');
btnStop.onclick = stop;
btnStop.disabled = true;
btnStart.disabled = true;
 
btnConnect= document.getElementById('btnConnect');
btnConnect.onclick = start;

var awsslink= document.getElementById('wsslink');

 
var rec_text="";  // for online rec asr result
var offline_text=""; // for offline rec asr result
var info_div = document.getElementById('info_div');

var upfile = document.getElementById('upfile');

 

var isfilemode=false;  // if it is in file mode
var file_ext="";
var file_sample_rate=16000; //for wav file sample rate
var file_data_array;  // array to save file data
 
var totalsend=0;


var now_ipaddress=window.location.href;
// 根据当前协议决定WebSocket协议
if(window.location.protocol === "https:") {
    now_ipaddress=now_ipaddress.replace("https://","wss://");
} else {
    now_ipaddress=now_ipaddress.replace("http://","ws://");
}
now_ipaddress=now_ipaddress.replace("static/index.html","");
var localport=window.location.port;
now_ipaddress=now_ipaddress.replace(localport,"10095");
document.getElementById('wssip').value=now_ipaddress;
addresschange();
function addresschange()
{   
	
    var Uri = document.getElementById('wssip').value; 
	document.getElementById('info_wslink').innerHTML="点此处手工授权（IOS手机）";
	Uri=Uri.replace(/wss/g,"https");
	console.log("addresschange uri=",Uri);
	
	awsslink.onclick=function(){
		window.open(Uri, '_blank');
		}
	
}

upfile.onclick=function()
{
		btnStart.disabled = true;
		btnStop.disabled = true;
		btnConnect.disabled=false;
	
}

// from https://github.com/xiangyuecn/Recorder/tree/master
var readWavInfo=function(bytes){
	//读取wav文件头，统一成44字节的头
	if(bytes.byteLength<44){
		return null;
	};
	var wavView=bytes;
	var eq=function(p,s){
		for(var i=0;i<s.length;i++){
			if(wavView[p+i]!=s.charCodeAt(i)){
				return false;
			};
		};
		return true;
	};
	
	if(eq(0,"RIFF")&&eq(8,"WAVEfmt ")){
 
		var numCh=wavView[22];
		if(wavView[20]==1 && (numCh==1||numCh==2)){//raw pcm 单或双声道
			var sampleRate=wavView[24]+(wavView[25]<<8)+(wavView[26]<<16)+(wavView[27]<<24);
			var bitRate=wavView[34]+(wavView[35]<<8);
			var heads=[wavView.subarray(0,12)],headSize=12;//head只保留必要的块
			//搜索data块的位置
			var dataPos=0; // 44 或有更多块
			for(var i=12,iL=wavView.length-8;i<iL;){
				if(wavView[i]==100&&wavView[i+1]==97&&wavView[i+2]==116&&wavView[i+3]==97){//eq(i,"data")
					heads.push(wavView.subarray(i,i+8));
					headSize+=8;
					dataPos=i+8;break;
				}
				var i0=i;
				i+=4;
				i+=4+wavView[i]+(wavView[i+1]<<8)+(wavView[i+2]<<16)+(wavView[i+3]<<24);
				if(i0==12){//fmt 
					heads.push(wavView.subarray(i0,i));
					headSize+=i-i0;
				}
			}
			if(dataPos){
				var wavHead=new Uint8Array(headSize);
				for(var i=0,n=0;i<heads.length;i++){
					wavHead.set(heads[i],n);n+=heads[i].length;
				}
				return {
					sampleRate:sampleRate
					,bitRate:bitRate
					,numChannels:numCh
					,wavHead44:wavHead
					,dataPos:dataPos
				};
			};
		};
	};
	return null;
};

// 添加文件处理状态标志
var fileProcessing = false;

upfile.onchange = function () {
　　　　　　var len = this.files.length;  
            for(let i = 0; i < len; i++) {
				file_ext=this.files[i].name.split('.').pop().toLowerCase();
				console.log("File extension:", file_ext);
				
				// 重置文件数据和状态
				file_data_array = undefined;
				fileProcessing = true;
				info_div.innerHTML='正在加载文件，请稍候...';
				
				if (file_ext === "mp3" || file_ext === "m4a" || file_ext === "aac") {
					// 对于压缩音频格式，使用Audio元素解码
					console.log("Processing compressed audio file:", file_ext);
					var audioElement = new Audio();
					var objectURL = URL.createObjectURL(this.files[i]);
					audioElement.src = objectURL;
					
					audioElement.addEventListener('loadeddata', function() {
						console.log("Audio loaded, duration:", audioElement.duration);
						console.log("Audio sample rate:", audioElement.sampleRate || "unknown");
						
						// 使用Web Audio API解码
						var audioContext = new (window.AudioContext || window.webkitAudioContext)();
						console.log("AudioContext sample rate:", audioContext.sampleRate);
						
						fetch(objectURL)
							.then(response => response.arrayBuffer())
							.then(arrayBuffer => {
								console.log("Fetched audio data, size:", arrayBuffer.byteLength);
								return audioContext.decodeAudioData(arrayBuffer);
							})
							.then(audioBuffer => {
								console.log("Audio decoded successfully");
								console.log("Sample rate:", audioBuffer.sampleRate);
								console.log("Channels:", audioBuffer.numberOfChannels);
								console.log("Duration:", audioBuffer.duration);
								console.log("Length:", audioBuffer.length);
								
								// 获取左声道数据（如果是立体声，只取左声道）
								var channelData = audioBuffer.getChannelData(0);
								console.log("Channel data length:", channelData.length);
								console.log("Channel data type:", channelData.constructor.name);
								console.log("First 10 samples:", Array.from(channelData.slice(0, 10)));
								
								// 重采样到16kHz（如果需要）
								var targetSampleRate = 16000;
								var resampledData;
								
								if (audioBuffer.sampleRate !== targetSampleRate) {
									console.log("Resampling from", audioBuffer.sampleRate, "to", targetSampleRate);
									var ratio = audioBuffer.sampleRate / targetSampleRate;
									var newLength = Math.round(channelData.length / ratio);
									resampledData = new Float32Array(newLength);
									
									for (var i = 0; i < newLength; i++) {
										var srcIndex = Math.round(i * ratio);
										resampledData[i] = channelData[srcIndex];
									}
									console.log("Resampled length:", resampledData.length);
								} else {
									resampledData = channelData;
								}
								
								// 转换为16位PCM
								var pcmData = new Int16Array(resampledData.length);
								for (var i = 0; i < resampledData.length; i++) {
									// 将Float32 (-1.0 to 1.0) 转换为 Int16 (-32768 to 32767)
									var sample = Math.max(-1, Math.min(1, resampledData[i]));
									pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
								}
								
								console.log("PCM data length:", pcmData.length);
								console.log("PCM first 10 samples:", Array.from(pcmData.slice(0, 10)));
								
								// 存储为ArrayBuffer
								file_data_array = pcmData.buffer;
								file_sample_rate = targetSampleRate;
								fileProcessing = false;
								
								info_div.innerHTML='✅ 文件加载完成！请点击连接进行识别';
								URL.revokeObjectURL(objectURL);
							})
							.catch(error => {
								console.error("Audio decoding failed:", error);
								fileProcessing = false;
								file_data_array = undefined;
								info_div.innerHTML='❌ 音频解码失败';
								alert("音频解码失败：" + error.message + "\n请尝试使用WAV格式的音频文件。");
							});
					});
					
					audioElement.addEventListener('error', function(e) {
						console.error("Audio loading failed:", e);
						fileProcessing = false;
						file_data_array = undefined;
						info_div.innerHTML='❌ 音频加载失败';
						alert("音频加载失败，请检查文件格式。");
					});
					
				} else {
					// 对于WAV等未压缩格式，使用原有逻辑
					console.log("Processing uncompressed audio file:", file_ext);
					let fileAudio = new FileReader();
					fileAudio.readAsArrayBuffer(this.files[i]);  
					
					var audioblob;
					fileAudio.onload = function() {
						audioblob = fileAudio.result;
						file_data_array=audioblob;
						fileProcessing = false;
						info_div.innerHTML='✅ 文件加载完成！请点击连接进行识别';
					}

					fileAudio.onerror = function(e) {
						console.log('error' + e);
						fileProcessing = false;
						file_data_array = undefined;
						info_div.innerHTML='❌ 文件读取失败';
					}
				}
            }
			// for wav file, we  get the sample rate
			if(file_ext=="wav")
            for(let i = 0; i < len; i++) {

                let fileAudio = new FileReader();
                fileAudio.readAsArrayBuffer(this.files[i]);  
                fileAudio.onload = function() {
                audioblob = new Uint8Array(fileAudio.result);
 
				// for wav file, we can get the sample rate
				var info=readWavInfo(audioblob);
				   console.log(info);
				   file_sample_rate=info.sampleRate;
	 
 
                }

　　　　　　 
            }
 
        }

function play_file()
{
		  var audioblob=new Blob( [ new Uint8Array(file_data_array)] , {type :"audio/wav"});
		  var audio_record = document.getElementById('audio_record');
		  audio_record.src =  (window.URL||webkitURL).createObjectURL(audioblob); 
          audio_record.controls=true;
		  //audio_record.play();  //not auto play
}
async function start_file_send()
{
	console.log("=== start_file_send called ===");
	
	// 检查文件是否正在处理
	if (fileProcessing) {
		console.error("❌ 错误：文件正在加载中！");
		info_div.innerHTML = "❌ 错误：文件正在加载中，请等待加载完成！";
		return;
	}
	
	// 检查是否已选择文件
	if (typeof file_data_array === 'undefined' || !file_data_array) {
		console.error("❌ 错误：未选择文件！");
		info_div.innerHTML = "❌ 错误：请先选择音频文件！";
		btnStart.disabled = false;
		btnConnect.disabled = false;
		return;
	}
	
	// 检查WebSocket连接状态
	if (typeof wsconnecter === 'undefined' || !wsconnecter) {
		console.error("❌ 错误：WebSocket连接器未初始化！");
		info_div.innerHTML = "❌ 错误：请先点击连接按钮建立WebSocket连接！";
		btnStart.disabled = false;
		btnConnect.disabled = false;
		return;
	}
	
	console.log("file_data_array type:", file_data_array ? file_data_array.constructor.name : "undefined", "length:", file_data_array ? file_data_array.length : 0);
	console.log("File size:", file_data_array && file_data_array.byteLength ? (file_data_array.byteLength / 1024 / 1024).toFixed(2) + " MB" : "unknown");
	console.log("file_ext:", file_ext);
	console.log("file_sample_rate:", file_sample_rate);
 
	var audioData;
	var startTime = Date.now();
 
	// 检查文件数据格式
	if (file_data_array instanceof ArrayBuffer) {
		console.log("File data is ArrayBuffer");
		
		// 如果是压缩音频格式，数据已经在上传时解码为PCM
		if (file_ext === "mp3" || file_ext === "m4a" || file_ext === "aac") {
			console.log("Using pre-decoded PCM data for compressed audio");
			sampleBuf = new Int16Array(file_data_array);
		}
		// 如果是WAV文件，跳过WAV文件头
		else if (file_ext === "wav") {
			console.log("Processing WAV file, skipping header");
			var uint8Array = new Uint8Array(file_data_array);
			
			// 检查WAV文件头
			var riffHeader = String.fromCharCode.apply(null, uint8Array.slice(0, 4));
			var waveHeader = String.fromCharCode.apply(null, uint8Array.slice(8, 12));
			console.log("RIFF header:", riffHeader);
			console.log("WAVE header:", waveHeader);
			
			if (riffHeader === "RIFF" && waveHeader === "WAVE") {
				// 跳过44字节的WAV文件头
				console.log("Valid WAV file, skipping 44-byte header");
				audioData = file_data_array.slice(44);
			} else {
				console.log("Invalid WAV header, using full data");
				audioData = file_data_array;
			}
			sampleBuf = new Int16Array(audioData);
		} else {
			console.log("Unknown file format, using full data");
			sampleBuf = new Int16Array(file_data_array);
		}
	} else if (file_data_array instanceof Uint8Array) {
		console.log("File data is Uint8Array, converting to Int16Array");
		// 将Uint8Array转换为Int16Array (假设是小端序16位PCM)
		var buffer = new ArrayBuffer(file_data_array.length);
		var uint8View = new Uint8Array(buffer);
		uint8View.set(file_data_array);
		sampleBuf = new Int16Array(buffer);
	} else {
		console.log("File data format unknown, using as-is");
		sampleBuf = new Uint8Array(file_data_array);
	}
 
	console.log("sampleBuf type:", sampleBuf.constructor.name, "length:", sampleBuf.length);
	console.log("sampleBuf first 10 values:", Array.from(sampleBuf.slice(0,10)));
 
	// 检查音频数据是否合理
	var maxValue = Math.max(...Array.from(sampleBuf.slice(0, Math.min(1000, sampleBuf.length))));
	var minValue = Math.min(...Array.from(sampleBuf.slice(0, Math.min(1000, sampleBuf.length))));
	console.log("Audio data range: min =", minValue, "max =", maxValue);
 
	var chunk_size=960; // for asr chunk_size [5, 10, 5]
	console.log("File mode chunk_size:", chunk_size);
	console.log("Total samples to send:", sampleBuf.length);
	console.log("Estimated chunks:", Math.ceil(sampleBuf.length / chunk_size));
	console.log("Estimated duration:", (sampleBuf.length / 16000).toFixed(2), "seconds");
 
	var totalChunks = Math.ceil(sampleBuf.length / chunk_size);
	var sentChunks = 0;
 
	while(sampleBuf.length>=chunk_size){
		sentChunks++;
		var progress = ((sentChunks / totalChunks) * 100).toFixed(1);
		console.log("=== Sending chunk", sentChunks, "/", totalChunks, "("+progress+"%) ===");
		
		sendBuf=sampleBuf.slice(0,chunk_size);
		totalsend=totalsend+sendBuf.length;
		sampleBuf=sampleBuf.slice(chunk_size,sampleBuf.length);
		
		// 确保发送正确的16位PCM格式
		if (sendBuf instanceof Int16Array) {
			var buffer = new ArrayBuffer(sendBuf.length * 2);
			var view = new Int16Array(buffer);
			view.set(sendBuf);
			wsconnecter.wsSend(buffer);
		} else {
			console.log("Sending Uint8Array chunk (legacy), length:", sendBuf.length);
			wsconnecter.wsSend(sendBuf);
		}
		
		// 更新界面进度
		info_div.innerHTML = "发送进度: " + progress + "% (" + sentChunks + "/" + totalChunks + " chunks)";
		
		console.log("Remaining sampleBuf length:", sampleBuf.length);
		
		// 每50个chunk暂停一下，避免阻塞浏览器
		if (sentChunks % 50 === 0) {
			console.log("Pausing after", sentChunks, "chunks to avoid blocking browser...");
			await new Promise(resolve => setTimeout(resolve, 10));
		}
	}
 
	// 发送剩余的音频数据
	if(sampleBuf.length > 0) {
		console.log("=== Sending final chunk ===");
		console.log("Final sampleBuf type:", sampleBuf.constructor.name, "length:", sampleBuf.length);
		var buffer = new ArrayBuffer(sampleBuf.length * 2);
		var view = new Int16Array(buffer);
		view.set(sampleBuf);
		console.log("Sending final buffer size:", buffer.byteLength, "first 4 bytes:", new Uint8Array(buffer.slice(0,4)));
		wsconnecter.wsSend(buffer);
		sampleBuf=new Int16Array();
	}
	
	// 发送结束信号但不立即停止连接
	var chunk_size = new Array( 5, 10, 5 );
	var request = {
		"chunk_size": chunk_size,
		"wav_name":  "h5",
		"is_speaking":  false,
		"chunk_interval":10,
		"mode":getAsrMode(),
	};
	console.log("Sending final request:", request);
	wsconnecter.wsSend( JSON.stringify(request) );
	
	info_div.innerHTML="文件已发送完成，正在等待识别结果...";
	
	// 启用停止按钮，让用户手动控制何时停止
	btnStop.disabled = false;
	btnStart.disabled = true;
	btnConnect.disabled = true;
}
 
	
function on_recoder_mode_change()
{
            var item = null;
            var obj = document.getElementsByName("recoder_mode");
            for (var i = 0; i < obj.length; i++) { //遍历Radio 
                if (obj[i].checked) {
                    item = obj[i].value;  
					break;
                }
		    

           }
		    if(item=="mic")
			{
				document.getElementById("mic_mode_div").style.display = 'block';
				document.getElementById("rec_mode_div").style.display = 'none';
 
 
		        btnStart.disabled = true;
		        btnStop.disabled = true;
		        btnConnect.disabled=false;
				isfilemode=false;
			}
			else
			{
				document.getElementById("mic_mode_div").style.display = 'none';
				document.getElementById("rec_mode_div").style.display = 'block';
 
		        btnStart.disabled = true;
		        btnStop.disabled = true;
		        btnConnect.disabled=true;
			    isfilemode=true;
				info_div.innerHTML='请点击选择文件';
			    
	 
			}
}


function getHotwords(){
	
	var obj = document.getElementById("varHot");

	if(typeof(obj) == 'undefined' || obj==null || obj.value.length<=0){
	  return null;
	}
	let val = obj.value.toString();
  
	console.log("hotwords="+val);
	let items = val.split(/[(\r\n)\r\n]+/);  //split by \r\n
	var jsonresult = {};
	const regexNum = /^[0-9]*$/; // test number
	for (item of items) {
  
		let result = item.split(" ");
		if(result.length>=2 && regexNum.test(result[result.length-1]))
		{ 
			var wordstr="";
			for(var i=0;i<result.length-1;i++)
				wordstr=wordstr+result[i]+" ";
  
			jsonresult[wordstr.trim()]= parseInt(result[result.length-1]);
		}
	}
	console.log("jsonresult="+JSON.stringify(jsonresult));
	return  JSON.stringify(jsonresult);

}
function getAsrMode(){

            var item = null;
            var obj = document.getElementsByName("asr_mode");
            for (var i = 0; i < obj.length; i++) { //遍历Radio 
                if (obj[i].checked) {
                    item = obj[i].value;  
					break;
                }
		    

           }
            if(isfilemode)
			{
				item= "offline";
			}
		   console.log("asr mode"+item);
		   
		   return item;
}
		   
function handleWithTimestamp(tmptext,tmptime)
{
	console.log( "tmptext: " + tmptext);
	console.log( "tmptime: " + tmptime);
    if(tmptime==null || tmptime=="undefined" || tmptext.length<=0)
	{
		return tmptext;
	}
	tmptext=tmptext.replace(/。|？|，|、|\?|\.|\ /g, ","); // in case there are a lot of "。"
	var words=tmptext.split(",");  // split to chinese sentence or english words
	var jsontime=JSON.parse(tmptime); //JSON.parse(tmptime.replace(/\]\]\[\[/g, "],[")); // in case there are a lot segments by VAD
	var char_index=0; // index for timestamp
	var text_withtime="";
	for(var i=0;i<words.length;i++)
	{   
	if(words[i]=="undefined"  || words[i].length<=0)
	{
		continue;
	}
    console.log("words===",words[i]);
	console.log( "words: " + words[i]+",time="+jsontime[char_index][0]/1000);
	if (/^[a-zA-Z]+$/.test(words[i]))
	{   // if it is english
		text_withtime=text_withtime+jsontime[char_index][0]/1000+":"+words[i]+"\n";
		char_index=char_index+1;  //for english, timestamp unit is about a word
	}
	else{
        // if it is chinese
		text_withtime=text_withtime+jsontime[char_index][0]/1000+":"+words[i]+"\n";
		char_index=char_index+words[i].length; //for chinese, timestamp unit is about a char
	}
	}
	return text_withtime;
	

}
// 语音识别结果; 对jsonMsg数据解析,将识别结果附加到编辑框中
function getJsonMessage( jsonMsg ) {
	//console.log(jsonMsg);
	console.log( "message: " + JSON.parse(jsonMsg.data)['text'] );
	var rectxt=""+JSON.parse(jsonMsg.data)['text'];
	var asrmodel=JSON.parse(jsonMsg.data)['mode'];
	var is_final=JSON.parse(jsonMsg.data)['is_final'];
	var timestamp=JSON.parse(jsonMsg.data)['timestamp'];
	if(asrmodel=="2pass-offline" || asrmodel=="offline")
	{
		
		offline_text=offline_text+handleWithTimestamp(rectxt,timestamp); //rectxt; //.replace(/ +/g,"");
		rec_text=offline_text;
	}
	else
	{
		rec_text=rec_text+rectxt; //.replace(/ +/g,"");
	}
	var varArea=document.getElementById('varArea');
	
	varArea.value=rec_text;
	console.log( "offline_text: " + asrmodel+","+offline_text);
	console.log( "rec_text: " + rec_text);
	if (isfilemode==true && is_final==true){
		console.log("File processing completed, but keeping connection open");
		play_file();
		
		info_div.innerHTML="识别完成！您可以点击停止按钮断开连接";
 
		btnStart.disabled = true;
		btnStop.disabled = false;  // 保持停止按钮可用
		btnConnect.disabled = true;
	}
	
	 
 
}

// 连接状态响应
function getConnState( connState ) {
	console.log("=== getConnState called with:", connState, "===");
	if ( connState === 0 ) { //on open
		console.log("WebSocket connected successfully");
		
		info_div.innerHTML='连接成功!请点击开始';
		if (isfilemode==true){
			info_div.innerHTML='请耐心等待,大文件等待时间更长';
			start_file_send();
		}
		else
		{
			// WebSocket连接成功后，启动录音
			console.log("Starting recording...");
			record();
			btnStart.disabled = false;
			btnStop.disabled = true;
			btnConnect.disabled=true;
		}
	} else if ( connState === 1 ) {
		//stop();
	} else if ( connState === 2 ) {
		stop();
		console.log( 'connecttion error' );
		 
		alert("连接地址"+document.getElementById('wssip').value+"失败,请检查asr地址和端口。或试试界面上手动授权，再连接。");
		btnStart.disabled = true;
		btnStop.disabled = true;
		btnConnect.disabled=false;
 
 
		info_div.innerHTML='请点击连接';
	}
}

function record()
{
	console.log("=== record() called ===");
	console.log("rec object:", rec);
 
	rec.open( function(){
		console.log("=== rec.open callback ===");
		rec.start();
		console.log("=== rec.start() called ===");
		console.log("开始");
		btnStart.disabled = true;
		btnStop.disabled = false;
		btnConnect.disabled=true;
	});
}

 

// 识别启动、停止、清空操作
function start() {
	console.log("=== start() called ===");
	
	// 如果是文件模式，检查文件状态
	if (isfilemode) {
		// 检查文件是否正在处理
		if (fileProcessing) {
			console.error("❌ 错误：文件正在加载中！");
			info_div.innerHTML = "❌ 错误：文件正在加载中，请等待加载完成！";
			return 0;
		}
		
		// 检查是否已选择文件
		if (typeof file_data_array === 'undefined' || !file_data_array) {
			console.error("❌ 错误：未选择文件！");
			info_div.innerHTML = "❌ 错误：请先选择音频文件！";
			return 0;
		}
	}
	
	// 清除显示
	clear();
	//控件状态更新
 	console.log("isfilemode"+isfilemode);
    
	//启动连接
	console.log("Calling wsconnecter.wsStart()");
	var ret=wsconnecter.wsStart();
	console.log("wsStart returned:", ret);
	// 1 is ok, 0 is error
	if(ret==1){
		info_div.innerHTML="正在连接asr服务器，请等待...";
		isRec = true;
		console.log("Set isRec to true");
		btnStart.disabled = true;
		btnStop.disabled = true;
		btnConnect.disabled=true;

        return 1;
	}
	else
	{
		info_div.innerHTML="请点击开始";
		btnStart.disabled = true;
		btnStop.disabled = true;
		btnConnect.disabled=false;

		return 0;
	}
}

 
function stop() {
		var chunk_size = new Array( 5, 10, 5 );
		var request = {
			"chunk_size": chunk_size,
			"wav_name":  "h5",
			"is_speaking":  false,
			"chunk_interval":10,
			"mode":getAsrMode(),
		};
		console.log(request);
		if(sampleBuf.length>0){
		// 创建新的ArrayBuffer确保正确的16位PCM格式
		console.log("Final sampleBuf type:", sampleBuf.constructor.name, "length:", sampleBuf.length);
		var buffer = new ArrayBuffer(sampleBuf.length * 2);
		var view = new Int16Array(buffer);
		view.set(sampleBuf);
		console.log("Sending final buffer size:", buffer.byteLength, "first 4 bytes:", new Uint8Array(buffer.slice(0,4)));
		wsconnecter.wsSend(buffer);
		console.log("sampleBuf.length"+sampleBuf.length);
		sampleBuf=new Int16Array();
		}
	   wsconnecter.wsSend( JSON.stringify(request) );
 
	  
	
	 

 
	// 控件状态更新
	
	isRec = false;
    info_div.innerHTML="发送完数据,请等候,正在识别...";

   if(isfilemode==false){
	    btnStop.disabled = true;
		btnStart.disabled = true;
		btnConnect.disabled=true;
		//wait 3s for asr result
	  setTimeout(function(){
		console.log("call stop ws!");
		wsconnecter.wsStop();
		btnConnect.disabled=false;
		info_div.innerHTML="请点击连接";}, 3000 );
 
 
	   
	rec.stop(function(blob,duration){
  
		console.log(blob);
		var audioBlob = Recorder.pcm2wav(data = {sampleRate:16000, bitRate:16, blob:blob},
		function(theblob,duration){
				console.log(theblob);
		var audio_record = document.getElementById('audio_record');
		audio_record.src =  (window.URL||webkitURL).createObjectURL(theblob); 
        audio_record.controls=true;
		//audio_record.play(); 
         	

	}   ,function(msg){
		 console.log(msg);
	}
		);
 

 
	},function(errMsg){
		console.log("errMsg: " + errMsg);
	});
   }
    // 停止连接
 
    

}

function clear() {
 
    var varArea=document.getElementById('varArea');
 
	varArea.value="";
    rec_text="";
	offline_text="";
 
}

 
function recProcess( buffer, powerLevel, bufferDuration, bufferSampleRate,newBufferIdx,asyncEnd ) {
	console.log("=== recProcess called ===");
	console.log("isRec:", isRec);
	console.log("buffer.length:", buffer.length);
	console.log("powerLevel:", powerLevel);
	console.log("bufferDuration:", bufferDuration);
	console.log("bufferSampleRate:", bufferSampleRate);
	
	if ( isRec === true ) {
		var data_48k = buffer[buffer.length-1];  
		console.log("data_48k type:", data_48k.constructor.name, "length:", data_48k.length);
		console.log("data_48k first 5 values:", Array.from(data_48k.slice(0,5)));
 
		var  array_48k = new Array(data_48k);
		console.log("array_48k length:", array_48k.length);
		
		var sampleResult = Recorder.SampleData(array_48k,bufferSampleRate,16000);
		console.log("SampleData result:", sampleResult);
		var data_16k = sampleResult.data;
		console.log("data_16k type:", data_16k.constructor.name, "length:", data_16k.length);
		console.log("data_16k first 5 values:", Array.from(data_16k.slice(0,5)));
 
		var oldSampleBufLength = sampleBuf.length;
		sampleBuf = Int16Array.from([...sampleBuf, ...data_16k]);
		console.log("sampleBuf length: before=" + oldSampleBufLength + ", after=" + sampleBuf.length + ", added=" + data_16k.length);
		
		var chunk_size=960; // for asr chunk_size [5, 10, 5]
		info_div.innerHTML=""+bufferDuration/1000+"s";
		
		console.log("Checking if sampleBuf.length(" + sampleBuf.length + ") >= chunk_size(" + chunk_size + ")");
		while(sampleBuf.length>=chunk_size){
			console.log("=== Sending chunk ===");
		    sendBuf=sampleBuf.slice(0,chunk_size);
			sampleBuf=sampleBuf.slice(chunk_size,sampleBuf.length);
			// 创建新的ArrayBuffer确保正确的16位PCM格式
			console.log("sendBuf type:", sendBuf.constructor.name, "length:", sendBuf.length);
			console.log("sendBuf first 5 values:", Array.from(sendBuf.slice(0,5)));
			var buffer = new ArrayBuffer(sendBuf.length * 2);
			var view = new Int16Array(buffer);
			view.set(sendBuf);
			console.log("Sending buffer size:", buffer.byteLength, "first 4 bytes:", new Uint8Array(buffer.slice(0,4)));
			wsconnecter.wsSend(buffer);
			console.log("Remaining sampleBuf length:", sampleBuf.length);
		}
	} else {
		console.log("isRec is false, skipping processing");
	}
}

function getUseITN() {
	var obj = document.getElementsByName("use_itn");
	for (var i = 0; i < obj.length; i++) {
		if (obj[i].checked) {
			return obj[i].value === "true";
		}
	}
	return false;
}
