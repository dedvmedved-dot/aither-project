import os,json,time,uuid,secrets,hashlib,logging,hmac
from datetime import datetime,timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Request,Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx,redis.asyncio as ra

M14="qwen-14b";M32="qwen-32b-base"
C14=os.environ.get("BFF_14B_BASE_URL","http://vllm-14b-instruct.aither-inference.svc:8000")
G32=os.environ.get("BFF_32B_GATEWAY_URL","http://nginx-gateway-32b.aither-inference.svc:8000")
TO=int(os.environ.get("BFF_REQUEST_TIMEOUT_SECONDS","300"))
RL_EN=os.environ.get("RATE_LIMIT_ENABLED","true").lower()=="true"
RURL=os.environ.get("REDIS_URL","redis://aither-redis-rate-limit.aither-inference.svc:6379/0")
RL_W=int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS","60"))
RL_M=int(os.environ.get("RATE_LIMIT_MAX_REQUESTS","10"))
ADM_U=os.environ.get("ADMIN_USERNAME","");ADM_PH=os.environ.get("ADMIN_PASSWORD_HASH","")
SESS_S=os.environ.get("SESSION_SECRET","");ATH_S=os.environ.get("AUTH_TOKEN_HASH_SECRET","")
B14T=os.environ.get("BFF_14B_UPSTREAM_AUTH_TOKEN","");B32T=os.environ.get("BFF_32B_GATEWAY_AUTH_TOKEN","")
TP="athr_";RNS="aither-auth";TNS=f"{RNS}:token";SNS=f"{RNS}:session"
# Identity service URL for delegate auth
IDH=os.environ.get("AITHER_IDENTITY_SERVICE_HOST","aither-identity")
IDP=os.environ.get("AITHER_IDENTITY_SERVICE_PORT_HTTP","8000")
IDURL=f"http://{IDH}:{IDP}/v1/identity/auth"
log=logging.getLogger("aither-bff");cli=None;rcli=None;ravail=False

async def rlkey(req):
    a=req.headers.get("authorization") or req.headers.get("Authorization") or ""
    if a: return f"rl:{hashlib.sha256(a.encode()).hexdigest()}"
    fwd=req.headers.get("x-forwarded-for","")
    ip=fwd.split(",")[0].strip() if fwd else (req.client.host if req.client else "unknown")
    return f"rl:ip:{ip}"

async def check_rl(req):
    global ravail
    if not RL_EN: return True
    if not ravail: log.warning("Redis unavailable — fail-open"); return True
    try:
        k=await rlkey(req);w=int(time.time())//RL_W;rk=f"{k}:{w}"
        c=await rcli.incr(rk)
        if c==1: await rcli.expire(rk,RL_W+5)
        if c>RL_M: log.warning("RL exceeded %s count=%d",k[:20],c); return False
        return True
    except Exception as e: log.error("RL error: %s — fail-open",e);ravail=False;return True

def vc():
    m=[]
    if not ADM_U: m.append("ADMIN_USERNAME")
    if not ADM_PH: m.append("ADMIN_PASSWORD_HASH")
    if not SESS_S: m.append("SESSION_SECRET")
    if not ATH_S: m.append("AUTH_TOKEN_HASH_SECRET")
    if not B14T: m.append("BFF_14B_UPSTREAM_AUTH_TOKEN")
    if not B32T: m.append("BFF_32B_GATEWAY_AUTH_TOKEN")
    return f"Missing: {', '.join(m)}" if m else ""

def htok(t): return hmac.new(ATH_S.encode(),t.encode(),hashlib.sha256).hexdigest()
def gentok(): r=TP+secrets.token_urlsafe(32); return r,htok(r)
def sk(s): return f"{SNS}:{s}"
def tmk(h): return f"{TNS}:{h}"
def thsk(): return f"{TNS}:all"
def ua(m): return B32T if m==M32 else B14T

async def load_tm(th):
    if not ravail: return None
    d=await rcli.get(tmk(th))
    if not d: return None
    try:
        m=json.loads(d)
        if m.get("revoked",False): return None
        m["last_used_at"]=datetime.now(timezone.utc).isoformat()
        await rcli.set(tmk(th),json.dumps(m)); return m
    except: return None

async def auth_req(req):
    sid=req.cookies.get("session_id","")
    ah=req.headers.get("authorization") or req.headers.get("Authorization") or ""
    if sid and ravail:
        sd=await rcli.get(sk(sid))
        if sd:
            try:
                s=json.loads(sd)
                req.state.auth_user=s.get("username","")
                req.state.auth_role=s.get("role","user")
                if s.get("username")==ADM_U: return True,"admin"
                return True,s.get("role","user")
            except: pass
    if ah.startswith("Bearer "):
        rt=ah[7:].strip();th=htok(rt);meta=await load_tm(th)
        if meta is None: return False,"Token not found or revoked"
        req.state.auth_user=meta.get("owner","")
        return True,meta.get("scopes",[])
    return False,"Auth required"

def ck(req,rs):
    sc=getattr(req.state,"auth_scope",None)
    if isinstance(sc,str) and sc=="admin": return True
    return isinstance(sc,list) and rs in sc

def cvt(messages):
    lines=[f"<|{m.get('role','user')}|>\n{m.get('content','')}" for m in messages]
    lines.append("<|assistant|>\n"); return "\n".join(lines)

@asynccontextmanager
async def lifespan(app):
    global cli,rcli,ravail
    cli=httpx.AsyncClient(timeout=TO)
    ai=vc()
    if ai: log.warning("Auth config issue: %s",ai)
    else: log.info("Auth config OK")
    try:
        rcli=ra.from_url(RURL,decode_responses=True)
        await rcli.ping();ravail=True;log.info("Redis connected")
    except Exception as e: rcli=None;ravail=False;log.warning("Redis unavailable: %s",e)
    yield
    if rcli: await rcli.aclose()
    await cli.aclose()

app=FastAPI(title="Aither BFF",version="0.5.0",lifespan=lifespan)
class CTReq(BaseModel): name:str=""; scopes:list=["model:14b:chat","model:32b:completion"]; expires_at:str=""
AEP={"/api/v1/models":{"GET"},"/api/v1/chat":{"POST"},"/api/v1/completions":{"POST"},"/api/v1/tokens":{"GET","POST"}}

@app.middleware("http")
async def amw(req:Request,call_next):
    p=req.url.path;m=req.method
    if p=="/health" or p.startswith("/api/v1/auth/"): return await call_next(req)
    if p in AEP and m in AEP[p]:
        ok,sc=await auth_req(req)
        if not ok: return JSONResponse(status_code=401,content={"error":sc})
        req.state.auth_ok=ok;req.state.auth_scope=sc
    return await call_next(req)

@app.get("/health")
async def health():
    return {"status":"ok","version":"0.5.0","rate_limit":"enabled" if RL_EN else "disabled",
            "redis":"connected" if ravail else "unavailable","auth":"configured" if not vc() else "partial"}

@app.post("/api/v1/auth/login")
async def login(req:Request):
    b=await req.json()
    if not b or not b.get("username") or not b.get("password"): raise HTTPException(400)
    u=b["username"];p=b["password"]
    # Try admin first
    if hmac.compare_digest(u,ADM_U):
        ph=hashlib.sha256(p.encode()).hexdigest()
        if hmac.compare_digest(ph,ADM_PH):
            if not ravail: raise HTTPException(503)
            sid=uuid.uuid4().hex
            sd=json.dumps({"username":u,"role":"administrator","user_id":0,"created_at":datetime.now(timezone.utc).isoformat(),"ip":req.client.host if req.client else "unknown"})
            await rcli.setex(sk(sid),86400,sd)
            r=JSONResponse(content={"status":"ok","session_id":sid,"user":{"username":u,"role":"administrator","id":0}})
            r.set_cookie(key="session_id",value=sid,max_age=86400,httponly=True,samesite="strict",secure=False)
            return r
    # Delegate to identity service for non-admin users
    try:
        async with httpx.AsyncClient(timeout=10) as ic:
            ir=await ic.post(IDURL,json={"username":u,"password":p})
            if ir.status_code==200:
                data=ir.json()
                ui=data.get("user",{})
                if not ravail: raise HTTPException(503)
                sid=uuid.uuid4().hex
                role=ui.get("role","user")
                sd=json.dumps({"username":u,"role":role,"user_id":ui.get("id"),"created_at":datetime.now(timezone.utc).isoformat(),"ip":req.client.host if req.client else "unknown"})
                await rcli.setex(sk(sid),86400,sd)
                resp=JSONResponse(content={"status":"ok","session_id":sid,"user":{"username":u,"role":role,"id":ui.get("id")}})
                resp.set_cookie(key="session_id",value=sid,max_age=86400,httponly=True,samesite="strict",secure=False)
                log.info("Login via identity: %s role=%s",u,role)
                return resp
    except Exception as e:
        log.warning("Identity login failed for %s: %s",u,e)
    raise HTTPException(401)

@app.post("/api/v1/auth/logout")
async def logout(): r=JSONResponse(content={"status":"logged_out"}); r.delete_cookie("session_id"); return r

@app.get("/api/v1/auth/me")
async def auth_me(req:Request):
    sid=req.cookies.get("session_id","")
    if not sid or not ravail: raise HTTPException(401)
    d=await rcli.get(sk(sid))
    if not d: raise HTTPException(401)
    try:
        s=json.loads(d)
        return {"username":s.get("username"),"role":s.get("role","user"),"id":s.get("user_id"),"created_at":s.get("created_at")}
    except: raise HTTPException(500)

@app.post("/api/v1/tokens")
async def create_token(req:Request):
    bd=await req.json();b=CTReq(**bd)
    ok,sc=await auth_req(req)
    if not ok: raise HTTPException(401)
    if not ravail: raise HTTPException(503)
    rt,th=gentok()
    owner=getattr(req.state,"auth_user","")
    meta={"token_id":uuid.uuid4().hex[:12],"token_hash":th,"name":b.name or "unnamed",
          "scopes":b.scopes or ["model:14b:chat"],"created_at":datetime.now(timezone.utc).isoformat(),
          "last_used_at":"","revoked":False,"revoked_at":"","owner":owner}
    await rcli.set(tmk(th),json.dumps(meta));await rcli.sadd(thsk(),th)
    return {"token_id":meta["token_id"],"token":rt,"name":meta["name"],"scopes":meta["scopes"],"created_at":meta["created_at"]}

@app.get("/api/v1/tokens")
async def list_tokens(req:Request):
    ok,sc=await auth_req(req)
    if not ok: raise HTTPException(401)
    if not ravail: raise HTTPException(503)
    owner=getattr(req.state,"auth_user","")
    is_admin=isinstance(sc,str) and sc=="admin"
    ths=await rcli.smembers(thsk());tokens=[]
    for th in ths:
        d=await rcli.get(tmk(th))
        if d:
            try:
                m=json.loads(d)
                # Multi-user isolation: non-admin users see only their own tokens
                if not is_admin and m.get("owner","")!=owner: continue
                tokens.append({"token_id":m.get("token_id"),"name":m.get("name"),"scopes":m.get("scopes"),
                               "created_at":m.get("created_at"),"last_used_at":m.get("last_used_at"),
                               "revoked":m.get("revoked",False),"revoked_at":m.get("revoked_at",""),
                               "owner":m.get("owner","")})
            except: pass
    return {"tokens":tokens}

@app.delete("/api/v1/tokens/{token_id}")
async def revoke_token(token_id:str,req:Request):
    ok,sc=await auth_req(req)
    if not ok: raise HTTPException(401)
    if not ravail: raise HTTPException(503)
    owner=getattr(req.state,"auth_user","")
    is_admin=isinstance(sc,str) and sc=="admin"
    ths=await rcli.smembers(thsk());found=False
    for th in ths:
        d=await rcli.get(tmk(th))
        if d:
            try:
                m=json.loads(d)
                if m.get("token_id")==token_id:
                    # Only admin or token owner can revoke
                    if not is_admin and m.get("owner","")!=owner:
                        raise HTTPException(403,detail="Not your token")
                    m["revoked"]=True;m["revoked_at"]=datetime.now(timezone.utc).isoformat()
                    await rcli.set(tmk(th),json.dumps(m));found=True;break
            except HTTPException: raise
            except: pass
    if not found: raise HTTPException(404)
    return {"status":"revoked","token_id":token_id}

@app.get("/api/v1/models")
async def list_models(req:Request):
    if not await check_rl(req): raise HTTPException(429)
    sc=getattr(req.state,"auth_scope",None)
    has=isinstance(sc,str) and sc=="admin"
    has=has or (isinstance(sc,list) and any(s.startswith("model:") for s in sc))
    if not has: raise HTTPException(403)
    return {"models":[{"id":"14b","name":M14,"type":"chat"},{"id":"32b","name":M32,"type":"completion"}]}

@app.post("/api/v1/chat")
async def chat(req:Request):
    b=await req.json();m=b.get("model","")
    if not await check_rl(req): raise HTTPException(429)
    if m in ("32b",M32):
        if not ck(req,"model:32b:chat-adapter"): raise HTTPException(403)
        p=cvt(b.get("messages",[]))
        cb={"model":M32,"prompt":p,"max_tokens":b.get("max_tokens",64),"temperature":b.get("temperature",0.0)}
        hd={"Content-Type":"application/json","Authorization":f"Bearer {ua(M32)}"}
        async with cli.stream("POST",f"{G32}/v1/completions",json=cb,headers=hd) as r:
            return Response(content=await r.aread(),status_code=r.status_code)
    if m in ("14b",M14):
        if not ck(req,"model:14b:chat"): raise HTTPException(403)
        b["model"]=M14
        hd={"Content-Type":"application/json","Authorization":f"Bearer {ua(M14)}"}
        async with cli.stream("POST",f"{C14}/v1/chat/completions",json=b,headers=hd) as r:
            return Response(content=await r.aread(),status_code=r.status_code)
    raise HTTPException(400)

@app.post("/api/v1/completions")
async def completions(req:Request):
    b=await req.json();m=b.get("model","")
    if not await check_rl(req): raise HTTPException(429)
    if m in ("32b",M32):
        if not ck(req,"model:32b:completion"): raise HTTPException(403)
        b["model"]=M32;hd={"Content-Type":"application/json","Authorization":f"Bearer {ua(M32)}"};u=f"{G32}/v1/completions"
    elif m in ("14b",M14):
        raise HTTPException(422)
    else: raise HTTPException(400)
    async with cli.stream("POST",u,json=b,headers=hd) as r:
        return Response(content=await r.aread(),status_code=r.status_code)

if __name__=="__main__":import uvicorn;uvicorn.run("app:app",host="0.0.0.0",port=8000)
