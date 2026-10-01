export type Audience="users"|"developers"|"operators"|"executives";
export type Category="Breaking"|"Security"|"Added"|"Fixed"|"Performance"|"Documentation"|"Changed"|"Internal";
export type EvidenceState="verified"|"attention"|"unknown";
export interface ReleaseEntry{id:string;title:string;category:Category;audiences:Audience[];included:boolean;evidence_refs:string[];paths:string[];uncertainty:string|null}
export interface Contributor{name:string;commits:number;commit_share_percent:number;files_touched:number;categories:Category[];first_at:string;last_at:string}
export interface EvidenceDomain{label:string;status:EvidenceState;detail:string;evidence_refs:string[]}
export interface ReleaseArtifact{schema_version:"1.0"|"1.1";readiness:"draft";source:Record<string,unknown>;audience:Audience;summary:Record<string,number>;entries:ReleaseEntry[];commits:Array<Record<string,unknown>>;files:Array<Record<string,unknown>>;risk_flags:Array<Record<string,unknown>>;collaboration?:{contributors:Contributor[];contributor_count:number;commit_span_hours:number;largest_commit_share_percent:number;interpretation:string};confidence?:{domains:EvidenceDomain[];security_delta:Record<string,Record<string,number>>;verified_domains:number;attention_domains:number};evidence:Record<string,unknown>;evidence_gaps:string[]}
