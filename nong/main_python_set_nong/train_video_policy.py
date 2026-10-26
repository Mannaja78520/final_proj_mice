"""Sequential Q-learning camera/pose trust gate, never a motor controller.

Actions alter accepted pose/heading and therefore future states and rewards.
Synthetic validation is reported separately from actual video acceptance.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np

FEATURES = ['invariant','raw','body','scene','confidence','held','heading']
BINS = [[3,12,35],[6,25,70],[2,10,30],[.05,.18],[.55,.8],[1,4,12],[3,12,35]]
ACTIONS = ['hold','accept','compensate','uncertain']


def unit(v):
    return v/max(1e-9,np.linalg.norm(v))


def wrap(v):
    return math.atan2(math.sin(v),math.cos(v))


def rotation(x,y,z):
    cx,sx,cy,sy,cz,sz=math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])


def difference(a,b,key='bones'):
    return float(np.rad2deg(np.arccos(np.clip(np.sum(a[key]*b[key],axis=1),-1,1))).max())


class CameraEpisode:
    def __init__(self,rng,heldout=False,length=36):
        self.rng=rng;self.heldout=heldout;self.length=length;self.i=0
        self.kind=int(rng.integers(0,5));self.camera=np.zeros(3)
        self.speed=float(rng.uniform(.6,1.6));self.proportion=float(rng.uniform(.75,1.3))
        self.accepted=None;self.previous=None;self.heading=0.;self.held=0
        self.last_output=None
        self.current=self.observe()
        self.accepted=self.current['observed'];self.previous=self.accepted

    def skeleton(self,t):
        phase=t*self.speed
        movement=self.kind in (1,3,4)
        amplitude=math.sin(phase*.32) if movement else 0
        twist=.22+(.3*math.sin(phase*.21) if self.kind in (3,4) else 0)
        roll=.05+(.12*math.sin(phase*.25) if self.kind==4 else 0)
        heading=.5*math.sin(phase*.18) if self.kind==3 else 0
        hip=.17*self.proportion;torso=.45*self.proportion
        p=np.zeros((33,3));p[23]=[hip,0,0];p[24]=[-hip,0,0]
        shoulder=rotation(0,twist,roll)@np.array([.2*self.proportion,0,0])
        p[11]=shoulder+[0,torso,0];p[12]=-shoulder+[0,torso,0]
        for a,(s,e,w) in enumerate([(11,13,15),(12,14,16)]):
            sign=1 if a==0 else -1
            upper=unit(np.array([sign*(.2+.65*amplitude),-.85+.5*amplitude,.2]))
            fore=unit(np.array([-sign*.45*amplitude,-.6+.8*amplitude,.25+.3*amplitude]))
            r=rotation(0,twist,roll)
            p[e]=p[s]+r@upper*.28*self.proportion;p[w]=p[e]+r@fore*.25*self.proportion
        return p@rotation(0,heading,0).T,heading

    @staticmethod
    def measure(p):
        left=unit(p[23]-p[24]);spine=p[11]+p[12]-p[23]-p[24]
        up=unit(spine-left*np.dot(left,spine));front=unit(np.cross(left,up))
        shoulder=p[11]-p[12];sx,sz=np.dot(shoulder,left),np.dot(shoulder,front)
        tl=unit(shoulder-up*np.dot(shoulder,up));tf=unit(np.cross(tl,up));basis=np.array([tl,up,tf])
        raw=np.array([unit(p[e]-p[s]) for s,e in [(11,13),(13,15),(12,14),(14,16)]])
        return dict(bones=raw@basis.T,raw=raw,twist=math.atan2(-sz,sx),
                    roll=math.atan2(np.dot(shoulder,up),math.hypot(sx,sz)),hipYaw=math.atan2(front[0],front[2]))

    def observe(self):
        truth,heading=self.skeleton(self.i)
        camera_event=self.kind in (2,4) and self.i in (7,16,25)
        if camera_event:
            yaw=self.rng.uniform(1.2,2.2) if self.heldout else self.rng.uniform(-1.0,1.0)
            pitch=self.rng.uniform(.55,1.0) if self.heldout else self.rng.uniform(-.4,.4)
            self.camera=np.array([pitch,yaw,self.rng.uniform(-.2,.2)])
        observed=truth@rotation(*self.camera).T
        noise=.003 if not self.heldout else .006
        observed+=self.rng.normal(0,noise,observed.shape)
        observed[:,2]*=self.rng.uniform(.85,1.15) # monocular depth bias
        confidence=float(self.rng.uniform(.8,1.0));occluded=self.rng.random()<.08
        if occluded:
            observed[13:17]+=self.rng.normal(0,.05,(4,3));confidence=float(self.rng.uniform(.25,.6))
        scene=float(self.rng.uniform(.25,.8) if camera_event else self.rng.uniform(0,.045))
        obs=self.measure(observed);true=self.measure(truth)
        return dict(observed=obs,truth=true,trueHeading=heading,scene=scene,confidence=confidence,
                    camera=camera_event,label='camera' if camera_event else 'motion' if self.kind in (1,3,4) else 'still')

    def features(self):
        b=self.current['observed'];a=self.accepted
        return dict(invariant=difference(b,a),raw=difference(b,self.previous,'raw'),
          body=math.degrees(max(abs(wrap(b['twist']-a['twist'])),abs(b['roll']-a['roll']))),
          scene=self.current['scene'],confidence=self.current['confidence'],held=self.held,
          heading=math.degrees(abs(wrap(b['hipYaw']-self.previous['hipYaw']))))

    def step(self,action):
        row=self.current;obs=row['observed'];previous=self.accepted
        if action=='accept' and not row['camera']:
            self.heading+=wrap(obs['hipYaw']-self.previous['hipYaw'])
        # Misclassifying camera movement as true motion is costly. In runtime
        # explicit cuts already fence heading; non-cut viewpoint changes remain.
        elif action=='accept' and row['camera']:
            self.heading+=wrap(obs['hipYaw']-self.previous['hipYaw'])
        if action in ('accept','compensate'):
            self.accepted=obs;self.held=0
        else:self.held+=1
        error=difference(self.accepted,row['truth'])
        body_error=math.degrees(abs(wrap(self.accepted['twist']-row['truth']['twist']))+abs(self.accepted['roll']-row['truth']['roll']))
        heading_error=math.degrees(abs(wrap(self.heading-row['trueHeading'])))
        jerk=difference(self.accepted,previous)
        reward=-(error+.4*body_error+.6*heading_error)/20-.004*jerk
        if row['confidence']<.55 and action in ('accept','compensate'):reward-=2
        if row['camera'] and action=='accept':reward-=3
        if self.held>4:reward-=min(2,(self.held-4)*.08)
        metric=dict(error=error,headingError=heading_error,label=row['label'],action=action,
                    falseCamera=bool(row['camera'] and action=='accept'))
        self.previous=obs;self.i+=1;done=self.i>=self.length
        if not done:self.current=self.observe()
        return reward,done,metric


class QTrainer:
    def __init__(self,seed):
        self.rng=np.random.default_rng(seed);self.q={};self.visits={}
    @staticmethod
    def key(features):
        return ':'.join(str(int(np.searchsorted(edges,features[name],side='right'))) for name,edges in zip(FEATURES,BINS))
    @staticmethod
    def analytic(f):
        if f['confidence']<.55:return 'uncertain'
        if f['scene']>.18 and f['invariant']<12 and f['body']<8:return 'compensate'
        if f['scene']<=.18 and (f['invariant']>3 or f['body']>2 or f['heading']>3):return 'accept'
        if f['invariant']<=3 and f['body']<=2:return 'hold'
        return 'uncertain'
    def train(self,episodes):
        for n in range(episodes):
            env=CameraEpisode(self.rng)
            while True:
                f=env.features();key=self.key(f);q=self.q.setdefault(key,np.zeros(4));self.visits[key]=self.visits.get(key,0)+1
                if self.rng.random()<.22:action=int(self.rng.integers(4))
                else:action=int(np.argmax(q))
                reward,done,_=env.step(ACTIONS[action])
                next_value=0 if done else float(self.q.get(self.key(env.features()),np.zeros(4)).max())
                q[action]+=.12*(reward+.85*next_value-q[action])
                if done:break
            if (n+1)%1000==0:print('Q episodes',n+1,'states',len(self.q),flush=True)
    def evaluate(self,seed,episodes,mode):
        rng=np.random.default_rng(seed);rows=[]
        for _ in range(episodes):
            env=CameraEpisode(rng,heldout=True)
            while True:
                f=env.features();key=self.key(f);q=self.q.get(key)
                if mode=='hold':action='hold'
                elif mode=='analytic' or q is None:action=self.analytic(f)
                else:
                    ranks=np.argsort(q)
                    action=ACTIONS[int(ranks[-1])] if q[ranks[-1]]-q[ranks[-2]]>=.5 else self.analytic(f)
                _,done,row=env.step(action);rows.append(row)
                if done:break
        camera=[r for r in rows if r['label']=='camera'];motion=[r for r in rows if r['label']=='motion'];still=[r for r in rows if r['label']=='still']
        return dict(episodes=episodes,frames=len(rows),meanBoneError=float(np.mean([r['error'] for r in rows])),
            meanHeadingError=float(np.mean([r['headingError'] for r in rows])),
            falseCameraAcceptance=float(np.mean([r['falseCamera'] for r in camera])),
            cameraRecall=float(np.mean([r['action']=='compensate' for r in camera])),
            motionAcceptance=float(np.mean([r['action'] in ('accept','compensate') for r in motion])),
            stillHoldRate=float(np.mean([r['action'] in ('hold','uncertain') for r in still])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--episodes',type=int,default=6000);parser.add_argument('--seed',type=int,default=1027)
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'web/video_motion_policy.json');args=parser.parse_args()
    trainer=QTrainer(args.seed);trainer.train(args.episodes)
    scores={mode:trainer.evaluate(args.seed+901,400,mode) for mode in ('learned','analytic','hold')}
    good=scores['learned']['falseCameraAcceptance']<=.05 and scores['learned']['meanBoneError']<=scores['analytic']['meanBoneError']*1.05
    model=dict(schema='mice-video-q-v1',version=1,algorithm='episodic-tabular-q-learning',seed=args.seed,
        enabled=good,features=FEATURES,bins=BINS,actions=ACTIONS,
        q={k:[round(float(x),5) for x in v] for k,v in trainer.q.items() if trainer.visits[k]>=5},
        validation=dict(syntheticOnly=True,heldoutUnseenCameraAngles=True,metrics=scores,acceptancePassed=good),
        training=dict(episodes=args.episodes,episodeFrames=36,discount=.85,learningRate=.12,exploration=.22,
          randomized=['camera yaw/pitch/roll','body proportions','speed','cuts with motion','occlusion','monocular depth bias','landmark noise'],
          actionChangesAcceptedState=True,noMotorActions=True))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(model,separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(enabled=good,states=len(model['q']),metrics=scores),indent=2),flush=True)
