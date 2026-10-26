// Exact production header/methods are injected; only peripherals and time are fake.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cctype>
#include <iostream>
#include <map>
#include <limits>
#include <string>
#include <type_traits>
#include <vector>
constexpr float PI = 3.14159265358979323846f;
#include "esp32_hardware_lift_module.h"
using std::max;
struct String : std::string {
 using std::string::string; using std::string::operator=;
 String()=default; String(const std::string& s):std::string(s){}
 template<class T, std::enable_if_t<std::is_arithmetic_v<T>,int> =0>
 String(T value,int =0):std::string(std::to_string(value)){}
 long toInt()const{return std::strtol(c_str(),nullptr,10);}
 float toFloat()const{return std::strtof(c_str(),nullptr);}
 void toUpperCase(){for(char& c:*this)c=(char)std::toupper((unsigned char)c);}
 bool equalsIgnoreCase(const char* other)const{
  if(size()!=std::strlen(other))return false;
  for(size_t i=0;i<size();++i)if(std::tolower((unsigned char)(*this)[i])!=std::tolower((unsigned char)other[i]))return false;
  return true;
 }
};
template<class T,class U,class V>T constrain(T value,U lo,V hi){return std::max<T>(T(lo),std::min<T>(value,T(hi)));}
constexpr int PWM_Max=1023, LOW=0, HIGH=1;
uint32_t clockMs=0;
uint32_t millis(){return clockMs;}
std::map<int,int> levels;
int digitalRead(int pin){return levels.count(pin)?levels[pin]:HIGH;}
struct Controller{int pwm=0;std::vector<int> history;void spin(int v){pwm=v;history.push_back(v);}};
struct ESP32Encoder{int64_t count=0;int64_t getCount(){return count;}void setCount(int64_t v){count=v;}};
struct HwConfig{
 struct Pins{int limitTop=22,limitDown=21;}pins;
 static bool pinUsable(int pin,bool){return pin>=0&&pin<=39&&!(pin>=6&&pin<=11);}
}hw;
#define GPIO_IS_VALID_GPIO(pin) HwConfig::pinUsable(pin,false)
struct Cell{
 double value=0;bool exists=false;
 bool isNull()const{return !exists;}
 template<class T>T as()const{return T(value);}
 template<class T>T operator|(T fallback)const{return exists?T(value):fallback;}
};
struct JsonVariant{
 std::map<std::string,double> data;
 bool isNull()const{return false;}
 Cell operator[](const char* key)const{auto it=data.find(key);return it==data.end()?Cell{}:Cell{it->second,true};}
};
struct JsonObject{};struct JsonArray{};struct JsonDocument{};
struct RgbStrip{
 void setColor(uint8_t,uint8_t,uint8_t){}void setBrightness(uint8_t){}
 bool setEffect(const String&){return true;}String effect()const{return "solid";}int brightness()const{return 0;}
};
struct AudioPlayer{
 int stopped=0;void stop(){stopped++;}void stopIfLooping(){}
 void playCmd(String[],int,String&){}void volCmd(String[],int,String&){}
 void ampCmd(String[],int,String&){}void streamCmd(String[],int,String&){}
};
struct Preferences{std::map<std::string,float> values;void putFloat(const char* key,float value){values[key]=value;}};
struct Module{
 virtual ~Module()=default;virtual const char* type()const{return "";}
 virtual void begin(){}virtual void loop(){}virtual bool handleCommand(String[],int,String&){return false;}
 virtual void addCapabilities(JsonArray){}virtual void status(JsonObject){}virtual bool busy(){return false;}
 virtual void silence(){}virtual void silenceLoop(){}virtual void applySettings(JsonVariant){}
};
#define private public
/*__HEADER__*/
#undef private
/*__METHODS__*/
// Unexercised peripheral/status virtuals are compiled on ESP32 by the firmware gate.
void LiftModule::begin(){}void LiftModule::loop(){}void LiftModule::addCapabilities(JsonArray){}void LiftModule::status(JsonObject){}
struct Fixture{
 Controller motor;LiftModule lift{nullptr};
 Fixture(){clockMs=0;levels.clear();hw.pins={22,21};lift.motor_=&motor;lift.deriveGeometry();}
 String command(const char* cmd,const char* arg=nullptr){String argv[2]={cmd,arg?arg:""},reply;lift.handleCommand(argv,arg?2:1,reply);return reply;}
};
int failures=0,passes=0;
void check(bool okay,const std::string& label){std::cout<<(okay?"CPP_PASS ":"CPP_FAIL ")<<label<<'\n';if(okay)passes++;else failures++;}
bool fault(Fixture& f,const char* why){return f.lift.faultReason_&&std::string(f.lift.faultReason_)==why;}
int main(){
 check(LIFT_TRAVEL_TIMEOUT_MS >= LIFT_TIMEOUT_MIN_MS && LIFT_TRAVEL_TIMEOUT_MS <= LIFT_TIMEOUT_MAX_MS &&
       LIFT_HOME_TIMEOUT_MS >= LIFT_TIMEOUT_MIN_MS && LIFT_HOME_TIMEOUT_MS <= LIFT_TIMEOUT_MAX_MS,
       "built-in travel and home deadlines are finite positive bounded values");
 for(const char* cmd:{"UP","DOWN","HOME"}){
  Fixture f;f.lift.travelTimeoutMs_=10;f.lift.homeTimeoutMs_=12;const uint32_t limit=std::string(cmd)=="HOME"?12:10;
  check(f.command(cmd).find("OK")==0,std::string(cmd)+" accepts valid request");
  f.lift.updateMotion();check(f.motor.pwm!=0,std::string(cmd)+" energizes before deadline");
  clockMs=limit-1;f.lift.updateMotion();check(f.motor.pwm!=0,std::string(cmd)+" deadline minus one still runs");
  clockMs=limit;f.lift.updateMotion();check(f.motor.pwm==0&&fault(f,std::string(cmd)=="HOME"?"home_timeout":"travel_timeout"),std::string(cmd)+" exact deadline cuts output and latches fault");
  check(f.lift.busy()&&f.lift.currentStage()==-1&&!f.lift.homed_,std::string(cmd)+" fault blocks sequence arrival and invalidates position");
  f.command("STOP");check(f.lift.busy()&&f.lift.faultReason_,std::string(cmd)+" STOP retains fault");
  check(f.command("HOME").find("ERR")==0&&f.motor.pwm==0,std::string(cmd)+" fault rejects new motion");
  clockMs+=100000;f.lift.updateMotion();check(f.motor.pwm==0,std::string(cmd)+" cannot restart after timeout");
  check(f.command("FAULT","CLEAR").find("OK")==0&&!f.lift.busy()&&f.motor.pwm==0,std::string(cmd)+" explicit clear stays stopped");
 }
 {Fixture f;clockMs=UINT32_MAX-5;f.lift.travelTimeoutMs_=10;f.command("UP");clockMs+=9;f.lift.updateMotion();check(f.motor.pwm>0,"wraparound deadline minus one runs");clockMs++;f.lift.updateMotion();check(f.motor.pwm==0&&fault(f,"travel_timeout"),"wraparound exact deadline stops");}
 {Fixture f;f.lift.travelTimeoutMs_=10;f.command("UP");clockMs=6;check(f.command("UP").find("ERR")==0,"repeated motion is refused");JsonVariant settings;settings.data["travel_timeout_ms"]=1000;f.lift.applySettings(settings);clockMs=10;f.lift.updateMotion();check(fault(f,"travel_timeout")&&f.motor.pwm==0,"repeat and changed setting cannot extend active snapshot");}
 {Fixture f;f.command("UP");f.lift.updateMotion();f.command("STOP");clockMs=LIFT_TRAVEL_TIMEOUT_MS+100;f.lift.updateMotion();check(!f.lift.faultReason_&&!f.lift.motionArmed_&&f.motor.pwm==0,"STOP cancels timer and motion without false later fault");}
 {Fixture f;levels[22]=LOW;f.command("UP");f.lift.updateMotion();check(f.motor.pwm==0&&!f.lift.busy(),"top limit stops UP normally");f.command("DOWN");f.lift.updateMotion();check(f.motor.pwm<0,"movement away from top is allowed");levels[21]=LOW;f.lift.updateMotion();check(f.motor.pwm==0&&fault(f,"limits_conflict"),"contradictory limits stop moving motor");check(f.command("FAULT","CLEAR").find("ERR")==0,"conflicting inputs cannot clear fault");}
 {Fixture f;levels[21]=LOW;f.command("HOME");f.lift.updateMotion();check(f.lift.homed_&&f.lift.currentStage()==0&&!f.lift.busy(),"bottom limit establishes home normally");}
 {Fixture f;levels[21]=LOW;levels[22]=LOW;f.lift.updateMotion();check(fault(f,"limits_conflict")&&f.motor.pwm==0,"contradictory idle inputs latch fault before any motion");}
 {Fixture f;hw.pins.limitDown=-1;check(f.command("UP").find("ERR")==0&&fault(f,"limits_missing")&&f.motor.pwm==0,"missing switch configuration refuses motor output");}
 {Fixture f;f.lift.travelTimeoutMs_=5;f.command("GOTO","3");f.lift.updateMotion();check(f.motor.pwm>0,"no-encoder top endpoint GOTO starts");clockMs=5;f.lift.updateMotion();check(fault(f,"travel_timeout")&&f.motor.pwm==0,"no-encoder endpoint GOTO is bounded");}
 {Fixture f;f.lift.hasEnc_=true;f.lift.homed_=true;f.lift.travelTimeoutMs_=5;f.command("GOTO","2");f.lift.updateMotion();check(f.motor.pwm>0,"encoder GOTO starts before stalled feedback");clockMs=5;f.lift.updateMotion();check(fault(f,"travel_timeout")&&f.motor.pwm==0,"stalled encoder GOTO reaches independent deadline");}
 {Fixture f;f.lift.hasEnc_=true;f.lift.homeTimeoutMs_=5;f.command("GOTO","2");clockMs=5;f.lift.updateMotion();check(fault(f,"home_timeout")&&f.lift.pendingStage_==-1,"failed homing cancels pending encoder GOTO");levels[21]=LOW;clockMs++;f.lift.updateMotion();check(f.motor.pwm==0,"late bottom switch cannot resume pending GOTO");}
 {Fixture f;f.lift.hasEnc_=true;f.lift.homeTimeoutMs_=5;f.lift.travelTimeoutMs_=8;f.command("GOTO","2");clockMs=3;levels[21]=LOW;f.lift.updateMotion();check(f.lift.state_==LiftModule::MOVE_GOTO&&f.lift.motionStartedMs_==3&&f.lift.motionTimeoutMs_==8,"HOME to GOTO starts a separately bounded travel phase");levels[21]=HIGH;clockMs=10;f.lift.updateMotion();check(f.motor.pwm>0,"pending GOTO runs until its own deadline");clockMs=11;f.lift.updateMotion();check(fault(f,"travel_timeout")&&f.motor.pwm==0,"pending GOTO own deadline stops output");}
 {Fixture f;check(f.command("GOTO","nonsense").find("ERR")==0&&!f.lift.busy(),"malformed GOTO cannot become stage zero");f.command("UP");check(f.command("FAULT","CLEAR").find("ERR")==0,"manual moving output must STOP before clear");}
 {Fixture f;f.lift.travelTimeoutMs_=10;f.command("UP");clockMs=10;levels[22]=LOW;f.lift.updateMotion();check(fault(f,"travel_timeout"),"deadline cannot be hidden by same-tick endpoint transition");}
 {Fixture f;for(double invalid:{0.0,-1.0,600001.0,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){JsonVariant v;v.data["travel_timeout_ms"]=invalid;v.data["home_timeout_ms"]=invalid;f.lift.applySettings(v);}check(f.lift.travelTimeoutMs_==LIFT_TRAVEL_TIMEOUT_MS&&f.lift.homeTimeoutMs_==LIFT_HOME_TIMEOUT_MS,"invalid SD timeout values retain finite defaults");JsonVariant v;v.data["travel_timeout_ms"]=1;v.data["home_timeout_ms"]=600000;f.lift.applySettings(v);check(f.lift.travelTimeoutMs_==1&&f.lift.homeTimeoutMs_==600000,"valid SD timeout boundaries apply");}
 {ConfigStore store;String why;for(const char* key:{"travel_timeout_ms","home_timeout_ms"}){check(!store.set(key,0,&why)&&!store.set(key,-1,&why)&&!store.set(key,600001,&why)&&!store.set(key,std::numeric_limits<float>::quiet_NaN(),&why),std::string(key)+" CFG rejects disable/invalid values");check(store.set(key,1,&why)&&store.set(key,600000,&why),std::string(key)+" CFG accepts both finite boundaries");}}
 check(passes>=35,"native scenario set completed");return failures?1:0;
}
