export type Audience="users"|"developers"|"operators"|"executives";
export type Category="Breaking"|"Security"|"Added"|"Fixed"|"Performance"|"Documentation"|"Changed"|"Internal";
export interface ReleaseEntry{id:string;title:string;category:Category;audiences:Audience[];included:boolean;evidence_refs:string[];paths:string[];uncertainty:string|null}
export interface ReleaseArtifact{schema_version:"1.0";readiness:"draft";source:Record<string,unknown>;audience:Audience;summary:Record<string,number>;entries:ReleaseEntry[];commits:Array<Record<string,unknown>>;files:Array<Record<string,unknown>>;risk_flags:Array<Record<string,unknown>>;evidence:Record<string,unknown>;evidence_gaps:string[]}
